import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
from pprint import pprint

from . import config
from .build import _BuildBackend
from .datastructures import BuildPaths, PackageInfo
from .cmd_runner import CommandRunner

from flit_core.config import ConfigError  # type: ignore


class _BuildComponentBackend(object):

    # --- Constructor ---------------------------------------------------------

    def __init__(self) -> None:
        self.runner: CommandRunner = CommandRunner()

    @property
    def verbose(self):
        return self.runner.verbose

    # --- Methods required by PEP 517 -----------------------------------------

    def get_requires_for_build_wheel(self, config_settings=None):
        """https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-wheel"""
        self.parse_config_settings(config_settings)

        comp_pyproject = Path('pyproject.toml').resolve()
        comp_cfg = self.read_component_config(comp_pyproject, config_settings,
                                              self.verbose)
        cfg = _BuildBackend.read_config(
            Path(comp_cfg.component['main_project']) / 'pyproject.toml',
            config_settings, self.verbose)
        return _BuildBackend.get_requires_build_project(
            config_settings, cfg, self.runner)

    def get_requires_for_build_editable(self, config_settings=None):
        """https://www.python.org/dev/peps/pep-0660/#get-requires-for-build-editable"""
        return self.get_requires_for_build_wheel(config_settings)

    def get_requires_for_build_sdist(self, config_settings=None):
        """https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-sdist"""
        return []

    def build_wheel(self,
                    wheel_directory,
                    config_settings=None,
                    metadata_directory=None):
        """https://www.python.org/dev/peps/pep-0517/#build-wheel"""
        assert metadata_directory is None

        # Parse options
        self.parse_config_settings(config_settings)

        # Build wheel
        with tempfile.TemporaryDirectory() as tmp_build_dir:
            whl_name = self.build_wheel_in_dir(wheel_directory, tmp_build_dir,
                                               config_settings)
        return whl_name

    def build_editable(self,
                       wheel_directory,
                       config_settings=None,
                       metadata_directory=None):
        raise NotImplementedError(
            "Editable installation not supported for individual components.")

    def build_sdist(self, sdist_directory, config_settings=None):
        raise NotImplementedError(
            "Source distribution not supported for individual components.")

    # --- Parsing config options and metadata ---------------------------------

    def parse_config_settings(self, config_settings: Optional[Dict]):
        self.runner.verbose = _BuildBackend.is_verbose_enabled(config_settings)

    @staticmethod
    def read_component_config(pyproject_path: Path,
                              config_settings: Optional[Dict],
                              verbose: bool) -> config.ComponentConfig:
        config_settings = config_settings or {}
        try:
            cfg = config.read_component_config(pyproject_path)
            if cfg.dynamic_metadata:
                raise ConfigError(
                    "Dynamic metadata not supported for components.")
        except ConfigError as e:
            e.args = ("\n"
                      "\n"
                      "\t❌ Error in user configuration:\n"
                      "\n"
                      f"\t\t{e}\n"
                      "\n", )
            raise
        except AssertionError as e:
            e.args = (
                "\n"
                "\n"
                "\t❌ Internal error while processing the configuration\n"
                "\t   Please notify the developers: https://github.com/tttapa/py-build-cmake/issues\n"
                "\n"
                f"\t\t{e}\n"
                "\n", )
            raise
        if verbose:
            _BuildComponentBackend.print_config_verbose(cfg)
        return cfg

    @staticmethod
    def read_all_metadata(src_dir, config_settings, verbose):
        from flit_core.common import Metadata
        cfg = _BuildComponentBackend.read_component_config(
            src_dir / 'pyproject.toml', config_settings, verbose)
        md_dict = {'name': cfg.package_name}
        md_dict.update(cfg.metadata)
        metadata = Metadata(md_dict)
        metadata.version = _BuildBackend.normalize_version(metadata.version)
        return cfg, metadata

    # --- Building wheels -----------------------------------------------------

    def build_wheel_in_dir(self,
                           wheel_directory_,
                           tmp_build_dir,
                           config_settings,
                           editable=False):
        """This is the main function that contains all steps necessary to build
        a complete wheel package, including the CMake builds etc."""
        comp_source_dir = Path().resolve()

        # Load metadata from the current (component) pyproject.toml file
        comp_cfg, comp_metadata = self.read_all_metadata(
            comp_source_dir, config_settings, self.verbose)

        # Set up all paths
        paths = BuildPaths(
            source_dir=Path(comp_cfg.component['main_project']),
            wheel_dir=Path(wheel_directory_),
            temp_dir=Path(tmp_build_dir),
            staging_dir=Path(tmp_build_dir) / 'staging',
            pkg_staging_dir=Path(tmp_build_dir) / 'staging',
        )

        # Load the config from the main pyproject.toml file
        cfg = _BuildBackend.read_config(paths.source_dir / 'pyproject.toml',
                                        config_settings, self.verbose)

        pkg_info = PackageInfo(
            version=comp_metadata.version,
            package_name=comp_cfg.package_name,
            module_name=cfg.module['name'],  # unused, CMake configuration only
        )

        # Create dist-info folder
        distinfo_dir = f'{pkg_info.package_name}-{pkg_info.version}.dist-info'
        distinfo_dir = paths.pkg_staging_dir / distinfo_dir
        os.makedirs(distinfo_dir, exist_ok=True)

        # Write metadata
        metadata_path = distinfo_dir / 'METADATA'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            comp_metadata.write_metadata_file(f)
        # Write or copy license
        _BuildBackend.write_license_files(comp_cfg.license, comp_source_dir,
                                          distinfo_dir)
        # Write entrypoints/scripts
        _BuildBackend.write_entrypoints(distinfo_dir, comp_cfg.entrypoints)

        # Configure, build and install the CMake project
        if cfg.cmake:
            self.do_cmake_build(comp_cfg, paths, cfg, pkg_info)

        # Create wheel
        whl_name = _BuildBackend.create_wheel(paths, cfg, pkg_info)
        return whl_name

    # --- Invoking CMake builds -----------------------------------------------

    def do_cmake_build(self, comp_cfg, paths: BuildPaths, cfg, pkg_info):
        """Configure, build and install using CMake."""

        cmake_cfg, native_cmake_cfg = _BuildBackend.get_cmake_configs(cfg)
        cmaker = _BuildBackend.get_cmaker(paths.source_dir,
                                          paths.staging_dir,
                                          cmake_cfg,
                                          cfg.cross,
                                          None,
                                          pkg_info,
                                          runner=self.runner)

        comp = comp_cfg.component
        if 'build_presets' in comp:
            cmaker.build_settings.presets = comp['build_presets']
        if 'install_presets' in comp:
            cmaker.install_settings.presets = comp['install_presets']
        if 'build_args' in comp:
            cmaker.build_settings.args = comp['build_args']
        if 'build_tool_args' in comp:
            cmaker.build_settings.tool_args = comp['build_tool_args']
        if 'install_args' in comp:
            cmaker.install_settings.args = comp['install_args']
        if 'install_components' in comp:
            cmaker.install_settings.components = comp['install_components']

        if not comp_cfg.component["install_only"]:
            cmaker.build()
        cmaker.install()

    # --- Misc helper functions -----------------------------------------------

    @staticmethod
    def print_config_verbose(cfg):
        print("\npy-build-cmake options")
        print("======================")
        print("component:")
        pprint(cfg.component)
        print("======================\n")


_BACKEND = _BuildComponentBackend()
get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
get_requires_for_build_editable = _BACKEND.get_requires_for_build_editable
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist
build_editable = _BACKEND.build_editable
