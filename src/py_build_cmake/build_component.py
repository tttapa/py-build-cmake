from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from .build import _BuildBackend as std_backend
from .commands.cmd_runner import CommandRunner
from .common import (
    ConfigError,
    PackageInfo,
    format_and_rethrow_exception,
)
from .common.platform import BuildPlatformInfo, determine_build_platform_info
from .config import load as config_load
from .export import metadata as export_metadata

logger = logging.getLogger(__name__)


class _BuildComponentBackend:
    # --- Constructor ---------------------------------------------------------

    def __init__(self) -> None:
        self.runner: CommandRunner = CommandRunner()
        self.plat: BuildPlatformInfo = determine_build_platform_info()

    @property
    def verbose(self):
        return self.runner.verbose

    # --- Methods required by PEP 517 -----------------------------------------

    def get_requires_for_build_wheel(self, config_settings=None):
        """https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-wheel"""
        try:
            self.parse_config_settings(config_settings)

            comp_source_dir = Path().resolve()
            comp_cfg = self.read_all_metadata(
                self.plat, comp_source_dir, config_settings, self.verbose
            )
            src_dir = comp_cfg.main_project.resolve()
            cfg = std_backend.read_config(
                self.plat, src_dir, config_settings, self.verbose
            )
            return std_backend.get_requires_build_project(
                self.plat, config_settings, cfg, self.runner
            )
        except Exception as e:
            format_and_rethrow_exception(e, component=True)

    def get_requires_for_build_editable(self, config_settings=None):
        """https://www.python.org/dev/peps/pep-0660/#get-requires-for-build-editable"""
        return self.get_requires_for_build_wheel(config_settings)

    def get_requires_for_build_sdist(self, config_settings=None):
        """https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-sdist"""
        return []

    def build_wheel(
        self, wheel_directory, config_settings=None, metadata_directory=None
    ):
        """https://www.python.org/dev/peps/pep-0517/#build-wheel"""
        try:
            assert metadata_directory is None

            # Parse options
            self.parse_config_settings(config_settings)

            # Build wheel
            with tempfile.TemporaryDirectory() as tmp_build_dir:
                return self.build_wheel_in_dir(
                    wheel_directory, tmp_build_dir, config_settings
                )
        except Exception as e:
            format_and_rethrow_exception(e, component=True)

    def build_editable(
        self, wheel_directory, config_settings=None, metadata_directory=None
    ):
        msg = "Editable installation not supported for individual components."
        raise NotImplementedError(msg)

    def build_sdist(self, sdist_directory, config_settings=None):
        msg = "Source distribution not supported for individual components."
        raise NotImplementedError(msg)

    # --- Parsing config options and metadata ---------------------------------

    def parse_config_settings(self, config_settings: dict | None):
        try:
            level = std_backend.get_log_level(config_settings)
            logging.basicConfig(level=level)
        except ValueError as e:
            logger.error("Invalid log level specified", exc_info=e)
        self.runner.verbose = std_backend.is_verbose_enabled(config_settings)
        self.runner.verbose_env = std_backend.is_verbose_env_enabled(config_settings)

    @staticmethod
    def read_all_metadata(
        plat: BuildPlatformInfo, src_dir: Path, config_settings, verbose: bool
    ):
        return config_load.read_full_component_config(
            plat, src_dir / "pyproject.toml", config_settings, verbose
        )

    # --- Building wheels -----------------------------------------------------

    def build_wheel_in_dir(
        self, wheel_dir, tmp_build_dir, config_settings, editable=False
    ):
        """This is the main function that contains all steps necessary to build
        a complete wheel package, including the CMake builds etc."""
        comp_source_dir = Path().resolve()

        # Load metadata from the current (component) pyproject.toml file
        comp_cfg = self.read_all_metadata(
            self.plat, comp_source_dir, config_settings, self.verbose
        )

        # Load the config from the main pyproject.toml file
        src_dir = comp_cfg.main_project.resolve()
        cfg, module = std_backend.read_all_metadata(
            self.plat, src_dir, config_settings, self.verbose
        )
        pkg_info = std_backend.get_pkg_info(comp_cfg, module)
        cmake_cfg = std_backend.get_cmake_config(self.plat, cfg)

        # Set up all paths
        paths = std_backend.get_default_paths(
            self.plat, wheel_dir, tmp_build_dir, src_dir, cfg
        )

        # Create dist-info folder
        distinfo_dir = f"{pkg_info.norm_name}-{pkg_info.version}.dist-info"
        distinfo_dir = paths.pkg_staging_dir / distinfo_dir
        distinfo_dir.mkdir(parents=True, exist_ok=True)

        # Write metadata, license and entry points to Wheel's distinfo
        export_metadata.write_metadata(comp_cfg, distinfo_dir)
        export_metadata.write_license_files(comp_cfg, src_dir, distinfo_dir)
        export_metadata.write_entry_points(comp_cfg, distinfo_dir)

        # Build and install the CMake project(s)
        sort_comp = sorted(comp_cfg.component.items(), key=lambda item: int(item[0]))
        components = {int(key): value for key, value in sort_comp}
        for k, component in components.items():
            if k not in cmake_cfg:
                msg = f"Index {k} in [tool.py-build-cmake.component] does not "
                msg += "refer to an existing CMake configuration in the main "
                msg += "project."
                raise ConfigError(msg)
            wheel_cfg = std_backend.get_wheel_config(self.plat, cfg)
            cmkcfg = cmake_cfg[k]
            build_cfg_name = std_backend.get_build_config_name(self.plat, cfg, k)
            path = cmkcfg["build_path"]
            path = str(path).replace("{build_config}", build_cfg_name)
            build_dir = Path(path)
            cmaker = self.get_cmaker(
                self.plat,
                paths.source_dir,
                build_dir,
                paths.staging_dir,
                cmkcfg,
                cfg.cross,
                wheel_cfg,
                pkg_info,
                component,
                runner=self.runner,
            )
            if not component["install_only"]:
                cmaker.build()
            cmaker.install()

        # Create wheel
        return std_backend.create_wheel(self.plat, paths, cfg, cmake_cfg, pkg_info)

    # --- CMake builds --------------------------------------------------------

    @staticmethod
    def get_cmaker(
        plat: BuildPlatformInfo,
        source_dir: Path,
        build_dir: Path,
        install_dir: Path | None,
        cmake_cfg: dict,
        cross_cfg: dict | None,
        wheel_cfg: dict,
        package_info: PackageInfo,
        component: dict,
        **kwargs,
    ):
        cmaker = std_backend.get_cmaker(
            plat=plat,
            source_dir=source_dir,
            build_dir=build_dir,
            install_dir=install_dir,
            cmake_cfg=cmake_cfg,
            cross_cfg=cross_cfg,
            wheel_cfg=wheel_cfg,
            package_info=package_info,
            **kwargs,
        )
        if "build_presets" in component:
            cmaker.build_settings.presets = component["build_presets"]
        if "build_args" in component:
            cmaker.build_settings.args = component["build_args"]
        if "build_tool_args" in component:
            cmaker.build_settings.tool_args = component["build_tool_args"]
        if "install_args" in component:
            cmaker.install_settings.args = component["install_args"]
        if "install_components" in component:
            cmaker.install_settings.components = component["install_components"]
        return cmaker


_BACKEND = _BuildComponentBackend()
get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
get_requires_for_build_editable = _BACKEND.get_requires_for_build_editable
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist
build_editable = _BACKEND.build_editable
