import platform
from pprint import pprint
import os
from pathlib import Path
from copy import copy
import shutil
import textwrap
from typing import Any, Dict, List, Optional
import tempfile
from glob import glob
import re

from . import config
from . import cmake
from .datastructures import BuildPaths, PackageInfo
from .cmd_runner import CommandRunner

from flit_core.common import Module as flit_Module  # type: ignore
from flit_core.config import ConfigError  # type: ignore
from distlib.version import NormalizedVersion  # type: ignore

_CMAKE_MINIMUM_REQUIRED = NormalizedVersion('3.15')


class _BuildBackend(object):

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

        pyproject = Path('pyproject.toml').resolve()
        cfg = _BuildBackend.read_config(pyproject, config_settings,
                                        self.verbose)
        return self.get_requires_build_project(config_settings, cfg,
                                               self.runner)

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
        """https://www.python.org/dev/peps/pep-0660/#build-editable"""
        assert metadata_directory is None

        # Parse options
        self.parse_config_settings(config_settings)

        # Build wheel
        with tempfile.TemporaryDirectory() as tmp_build_dir:
            whl_name = self.build_wheel_in_dir(wheel_directory,
                                               tmp_build_dir,
                                               config_settings,
                                               editable=True)
        return whl_name

    def build_sdist(self, sdist_directory, config_settings=None):
        """https://www.python.org/dev/peps/pep-0517/#build-sdist"""
        sdist_directory = Path(sdist_directory)
        src_dir = Path().resolve()

        # Parse options
        self.parse_config_settings(config_settings)

        # Load metadata
        from flit_core.common import make_metadata
        pyproject = src_dir / 'pyproject.toml'
        cfg = self.read_config(pyproject, config_settings, self.verbose)
        import_name = cfg.module['name']
        pkg = flit_Module(import_name, src_dir / cfg.module['directory'])
        metadata = make_metadata(pkg, cfg)
        metadata.version = self.normalize_version(metadata.version)

        # Export dist
        from flit_core.sdist import SdistBuilder  # type: ignore
        rel_pyproject = os.path.relpath(pyproject, src_dir)
        extra_files = [str(rel_pyproject)] + cfg.referenced_files
        sdist_cfg = cfg.sdist['cross' if cfg.cross else self.get_os_name()]
        sdist_builder = SdistBuilder(
            pkg,
            metadata=metadata,
            cfgdir=src_dir,
            reqs_by_extra=None,
            entrypoints=cfg.entrypoints,
            extra_files=extra_files,
            data_directory=None,
            include_patterns=sdist_cfg.get('include_patterns', []),
            exclude_patterns=sdist_cfg.get('exclude_patterns', []),
        )
        sdist_tar = sdist_builder.build(Path(sdist_directory))
        return os.path.relpath(sdist_tar, sdist_directory)

    # --- Parsing config options and metadata ---------------------------------

    @staticmethod
    def is_verbose_enabled(config_settings: Optional[dict]):
        if 'PY_BUILD_CMAKE_VERBOSE' in os.environ:
            return True
        if config_settings is None:
            return False
        if config_settings.keys() & {'verbose', '--verbose', 'V', '-V'}:
            return True
        return False

    def parse_config_settings(self, config_settings: Optional[Dict]):
        self.runner.verbose = self.is_verbose_enabled(config_settings)

    @staticmethod
    def read_config(pyproject_path: Path, config_settings: Optional[Dict],
                    verbose: bool) -> config.Config:
        config_settings = config_settings or {}
        try:
            if verbose:
                print("Configuration settings:")
                pprint(config_settings)
            listify = lambda x: x if isinstance(x, list) else [x]
            keys = ['--local', '--cross']
            overrides = {
                key: listify(config_settings.get(key) or [])
                for key in keys
            }
            if verbose:
                print("Configuration settings for local and "
                      "cross-compilation overrides:")
                pprint(overrides)
            cfg = config.read_config(pyproject_path, overrides)
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
            _BuildBackend.print_config_verbose(cfg)
        return cfg

    @staticmethod
    def get_requires_build_project(config_settings: Optional[dict],
                                   cfg: config.Config, runner: CommandRunner):
        deps: List[str] = []
        # Check if we need CMake
        if cfg.cmake:
            _BuildBackend.check_cmake_program(cfg, deps, runner)
        if cfg.stubgen:
            _BuildBackend.check_stubgen_program(deps, runner)
        if runner.verbose:
            print('Dependencies for build:', deps)
        return deps

    # --- Building wheels -----------------------------------------------------

    def build_wheel_in_dir(self,
                           wheel_directory_,
                           tmp_build_dir,
                           config_settings,
                           editable=False):
        """This is the main function that contains all steps necessary to build
        a complete wheel package, including the CMake builds etc."""
        # Set up all paths
        paths = BuildPaths(
            source_dir=Path().resolve(),
            wheel_dir=Path(wheel_directory_),
            temp_dir=Path(tmp_build_dir),
            staging_dir=Path(tmp_build_dir) / 'staging',
            pkg_staging_dir=Path(tmp_build_dir) / 'staging',
        )

        # Load metadata from the pyproject.toml file
        cfg, pkg, metadata = _BuildBackend.read_all_metadata(
            paths.source_dir, config_settings, self.verbose)

        pkg_info = PackageInfo(
            version=metadata.version,
            package_name=cfg.package_name,
            module_name=cfg.module['name'],
        )

        # Copy the module's Python source files to the temporary folder
        if not editable:
            self.copy_pkg_source_to(paths.staging_dir, pkg)
        else:
            paths = self.do_editable_install(cfg, paths, pkg)

        # Create dist-info folder
        distinfo_dir = f'{pkg_info.package_name}-{pkg_info.version}.dist-info'
        distinfo_dir = paths.pkg_staging_dir / distinfo_dir
        os.makedirs(distinfo_dir, exist_ok=True)

        # Write metadata
        metadata_path = distinfo_dir / 'METADATA'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            metadata.write_metadata_file(f)
        # Write or copy license
        self.write_license_files(cfg.license, paths.source_dir, distinfo_dir)
        # Write entrypoints/scripts
        self.write_entrypoints(distinfo_dir, cfg.entrypoints)

        # Generate .pyi stubs (for the Python files only)
        if cfg.stubgen is not None and not editable:
            self.generate_stubs(paths, pkg, cfg.stubgen)

        # Configure, build and install the CMake project
        if cfg.cmake:
            self.do_native_cross_cmake_build(paths, cfg, pkg_info)

        # Create wheel
        whl_name = self.create_wheel(paths, cfg, pkg_info)
        return whl_name

    @staticmethod
    def read_all_metadata(src_dir, config_settings, verbose):
        from flit_core.common import make_metadata, ProblemInModule
        cfg = _BuildBackend.read_config(src_dir / 'pyproject.toml',
                                        config_settings, verbose)
        pkg = flit_Module(cfg.module['name'], src_dir / cfg.module['directory'])
        try:
            metadata = make_metadata(pkg, cfg)
        except ImportError as e:
            if hasattr(e, "msg"):
                e.msg = (
                    "\n"
                    "\n"
                    f"\t❌ Error importing {pkg.name} for reading metadata:\n"
                    "\n"
                    f"\t\t{e.msg}\n"
                    "\n")
            raise
        except ProblemInModule as e:
            e.args = ("\n"
                      "\n"
                      f"\t❌ Error reading metadata from {pkg.name}:"
                      "\n"
                      "\n"
                      f"\t\t{e}\n"
                      "\n", )
            raise
        metadata.version = _BuildBackend.normalize_version(metadata.version)
        metadata.name = cfg.package_name
        return cfg, pkg, metadata

    @staticmethod
    def create_wheel(paths, cfg, package_info):
        """Create a wheel package from the build directory."""
        from distlib.wheel import Wheel  # type: ignore
        whl = Wheel()
        whl.name = package_info.package_name
        whl.version = package_info.version
        pure = _BuildBackend.is_pure(cfg)
        libdir = 'purelib' if pure else 'platlib'
        staging_dir = paths.pkg_staging_dir
        whl_paths = {'prefix': str(staging_dir), libdir: str(staging_dir)}
        whl.dirname = paths.wheel_dir
        if pure:
            tags = {'pyver': ['py3']}
        elif cfg.cross:
            tags = _BuildBackend.get_cross_tags(cfg.cross)
            tags = _BuildBackend.convert_wheel_tags(tags, cfg)
        else:
            tags = _BuildBackend.get_native_tags()
            tags = _BuildBackend.convert_wheel_tags(tags, cfg)
        wheel_path = whl.build(whl_paths, tags=tags, wheel_version=(1, 0))
        whl_name = os.path.relpath(wheel_path, paths.wheel_dir)
        return whl_name

    @staticmethod
    def get_cmake_configs(cfg):
        native_cmake_cfg = cfg.cmake[_BuildBackend.get_os_name()]
        cmake_cfg = cfg.cmake['cross'] if cfg.cross else native_cmake_cfg
        return cmake_cfg, native_cmake_cfg

    def do_native_cross_cmake_build(self, paths: BuildPaths, cfg,
                                    package_info):
        """If not cross-compiling, just do a regular CMake build+install.
        When cross-compiling, do a cross-build+install (using the provided 
        CMake toolchain file).
        If cfg.cross['copy_from_native_build'] is set, before cross-compiling, 
        first a normal build+install is performed to a separate directory, then
        the cross-build+install is performed, and finally the installed files
        from the native build that match the patterns in
        cfg.cross['copy_from_native_build'] are copied to the installation
        directory of the cross-build for packaging."""
        cmake_cfg, native_cmake_cfg = self.get_cmake_configs(cfg)
        # When cross-compiling, optionally do a native build first
        native_install_dir = None
        if self.needs_cross_native_build(cfg):
            native_install_dir = paths.temp_dir / 'native-install'
            self.run_cmake(paths.source_dir, native_install_dir,
                           native_cmake_cfg, None, package_info,
                           native_install_dir)
        # Then do the actual build
        self.run_cmake(paths.source_dir, paths.staging_dir, cmake_cfg,
                       cfg.cross, package_info, native_install_dir)
        # Finally, move the files from the native build to the staging area
        if native_install_dir:
            self.copy_native_install(paths.staging_dir, native_install_dir,
                                     cfg.cross['copy_from_native_build'])

    def copy_native_install(self, staging_dir, native_install_dir,
                            native_install_patterns):
        """Copy the files that match the patterns from the native installation
        directory to the wheel staging directory."""
        for pattern in native_install_patterns:
            matches = sorted(glob(str(native_install_dir / pattern)))
            for path in matches:
                path = Path(path)
                rel = path.relative_to(native_install_dir)
                path.parent.mkdir(parents=True, exist_ok=True)
                print('-- Moving:', path, '->', staging_dir / rel.parent)
                shutil.move(path, staging_dir / rel.parent)
                # TODO: what if the folder already exists?
            if not matches:
                raise RuntimeError(
                    "Native build installed no files that matched the "
                    "pattern '" + pattern + "'")
        shutil.rmtree(native_install_dir)

    # --- Files installation --------------------------------------------------

    @staticmethod
    def copy_pkg_source_to(staging_dir: Path,
                           pkg: flit_Module,
                           symlink: bool = False):
        """Copy the files of a Python package to the build directory."""
        for mod_file in pkg.iter_files():
            rel_path = os.path.relpath(mod_file, pkg.path.parent)
            dst = staging_dir / rel_path
            os.makedirs(dst.parent, exist_ok=True)
            if symlink:
                dst.symlink_to(mod_file, target_is_directory=False)
            else:
                shutil.copy2(mod_file, dst, follow_symlinks=False)

    @staticmethod
    def write_license_files(license, srcdir: Path, distinfo_dir: Path):
        """Write the LICENSE file from pyproject.toml to the distinfo
        directory."""
        if 'text' in license:
            with (distinfo_dir / 'LICENSE').open('w', encoding='utf-8') as f:
                f.write(license['text'])
        elif 'file' in license:
            assert not Path(license['file']).is_absolute()
            shutil.copy2(srcdir / license['file'], distinfo_dir)

    @staticmethod
    def write_entrypoints(distinfo: Path, entrypoints: Dict[str, Dict[str,
                                                                      str]]):
        from flit_core.common import write_entry_points
        with (distinfo / 'entry_points.txt').open('w', encoding='utf-8') as f:
            write_entry_points(entrypoints, f)

    # --- Editable installs ---------------------------------------------------

    def do_editable_install(self, cfg, paths: BuildPaths, pkg: flit_Module):
        edit_cfg = cfg.editable['cross' if cfg.cross else self.get_os_name()]
        mode = edit_cfg["mode"]
        if mode == "wrapper":
            self.write_editable_wrapper(paths.staging_dir, pkg)
        elif mode == "hook":
            self.write_editable_hook(paths.staging_dir, pkg),
        elif mode == "symlink":
            paths = self.write_editable_links(paths, pkg)
        else:
            assert False, "Invalid editable mode"
        return paths

    def write_editable_wrapper(self, staging_dir: Path, pkg: flit_Module):
        """Write a fake __init__.py file that points to the development 
        folder."""
        tmp_pkg: Path = staging_dir / pkg.name
        pkgpath = Path(pkg.path)
        initpath = pkgpath / '__init__.py'
        os.makedirs(tmp_pkg, exist_ok=True)
        special_dunders = [
            '__builtins__', '__cached__', '__file__', '__loader__', '__name__',
            '__package__', '__path__', '__spec__'
        ]
        content = f"""\
            # First extend the search path with the development folder
            __spec__.submodule_search_locations.insert(0, {str(pkgpath)!a})
            # Now manually import the development __init__.py
            from importlib import util as _util
            _spec = _util.spec_from_file_location("{pkg.name}",
                                                  {str(initpath)!a})
            _mod = _util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            # After importing, add its symbols to our global scope
            _vars = _mod.__dict__.copy()
            for _k in ['{"','".join(special_dunders)}']: _vars.pop(_k)
            globals().update(_vars)
            # Clean up
            del _k, _spec, _mod, _vars, _util
            """
        (tmp_pkg / '__init__.py').write_text(textwrap.dedent(content),
                                             encoding='utf-8')
        # Add the py.typed file if it exists, so mypy picks up the stubs for
        # the C++ extensions
        py_typed: Path = pkg.path / 'py.typed'
        if py_typed.exists():
            shutil.copy2(py_typed, tmp_pkg)
        # Write a path file so IDEs find the correct files as well
        (staging_dir / f'{pkg.name}.pth').write_text(str(pkg.path.parent))

    def write_editable_hook(self, staging_dir: Path, pkg: flit_Module):
        # Write a hook that finds the installed compiled extension modules
        pkg_hook: Path = staging_dir / (pkg.name + '_editable_hook')
        os.makedirs(pkg_hook, exist_ok=True)
        content = f"""\
            import sys, inspect, os
            from importlib.machinery import PathFinder

            class EditablePathFinder(PathFinder):
                def __init__(self, name, extra_path):
                    self.name = name
                    self.extra_path = extra_path
                def find_spec(self, name, path=None, target=None):
                    if name.split('.', 1)[0] != self.name:
                        return None
                    path = (path or []) + [self.extra_path]
                    return super().find_spec(name, path, target)

            def install(name: str):
                source_path = os.path.abspath(inspect.getsourcefile(EditablePathFinder))
                source_dir = os.path.dirname(source_path)
                installed_path = os.path.join(source_dir, '..', name)
                sys.meta_path.insert(0, EditablePathFinder(name, installed_path))

            install('{pkg.name}')
            """
        (pkg_hook / '__init__.py').write_text(textwrap.dedent(content),
                                              encoding='utf-8')
        # Write a path file to find the development files
        content = f"""\
            {str(pkg.path.parent)}
            import {pkg.name}_editable_hook"""
        (staging_dir / f'{pkg.name}.pth').write_text(textwrap.dedent(content))

    def write_editable_links(self, paths: BuildPaths, pkg: flit_Module):
        paths = copy(paths)
        cache_dir = paths.source_dir / '.py-build-cmake_cache'
        cache_dir.mkdir(exist_ok=True)
        paths.staging_dir = cache_dir / 'editable'
        shutil.rmtree(paths.staging_dir, ignore_errors=True)
        paths.staging_dir.mkdir()
        self.copy_pkg_source_to(paths.staging_dir, pkg, symlink=True)
        pth_file = paths.pkg_staging_dir / f'{pkg.name}.pth'
        pth_file.parent.mkdir(exist_ok=True)
        pth_file.write_text(str(paths.staging_dir))
        return paths

    # --- Invoking CMake builds -----------------------------------------------

    def run_cmake(self, pkgdir, install_dir, cmake_cfg, cross_cfg,
                  package_info, native_install_dir):
        """Configure, build and install using CMake."""

        cmaker = self.get_cmaker(pkgdir,
                                 install_dir,
                                 cmake_cfg,
                                 cross_cfg,
                                 native_install_dir,
                                 package_info,
                                 runner=self.runner)

        cmaker.configure()
        cmaker.build()
        cmaker.install()

    @staticmethod
    def get_cmaker(pkg_dir: Path, install_dir: Optional[Path], cmake_cfg: dict,
                   cross_cfg: Optional[dict],
                   native_install_dir: Optional[Path],
                   package_info: PackageInfo, **kwargs):
        # Optionally include the cross-compilation settings
        if cross_cfg:
            cross_compiling = True
            cross_opts = {
                'toolchain_file': cross_cfg.get('toolchain_file'),
                'python_prefix': cross_cfg.get('prefix'),
                'python_library': cross_cfg.get('library'),
            }
        else:
            cross_compiling = False
            cross_keys = 'toolchain_file', 'python_prefix', 'python_library'
            cross_opts = {k: None for k in cross_keys}

        # Add some CMake configure options
        options = cmake_cfg.get('options', {})
        if native_install_dir:
            options['PY_BUILD_CMAKE_NATIVE_INSTALL_DIR:PATH'] = \
                str(native_install_dir)
        btype = cmake_cfg.get('build_type')
        if btype:  # -D CMAKE_BUILD_TYPE={type}
            options['CMAKE_BUILD_TYPE:STRING'] = btype

        # Build folder for each platform
        build_cfg_name = _BuildBackend.get_build_config_name(cross_cfg)

        # CMake options
        return cmake.CMaker(
            cmake_settings=cmake.CMakeSettings(
                working_dir=Path(pkg_dir),
                source_path=Path(cmake_cfg["source_path"]),
                build_path=Path(cmake_cfg['build_path']) / build_cfg_name,
                os=_BuildBackend.get_os_name(),
                find_python=bool(cmake_cfg["find_python"]),
                find_python3=bool(cmake_cfg["find_python3"]),
                command=Path("cmake"),
            ),
            conf_settings=cmake.CMakeConfigureSettings(
                environment=cmake_cfg.get("env", {}),
                build_type=cmake_cfg.get('build_type'),
                options=options,
                args=cmake_cfg.get('args', []),
                preset=cmake_cfg.get('preset'),
                generator=cmake_cfg.get('generator'),
                cross_compiling=cross_compiling,
                **cross_opts,
            ),
            build_settings=cmake.CMakeBuildSettings(
                args=cmake_cfg['build_args'],
                tool_args=cmake_cfg['build_tool_args'],
                presets=cmake_cfg.get('build_presets', []),
                configs=cmake_cfg.get('config', []),
            ),
            install_settings=cmake.CMakeInstallSettings(
                args=cmake_cfg['install_args'],
                presets=cmake_cfg.get('install_presets', []),
                configs=cmake_cfg.get('config', []),
                components=cmake_cfg.get('install_components', []),
                prefix=install_dir,
            ),
            package_info=package_info,
            **kwargs,
        )

    # --- Generate stubs ------------------------------------------------------

    def generate_stubs(self, paths: BuildPaths, pkg, cfg: Dict[str, Any]):
        """Generate stubs (.pyi) using mypy stubgen."""
        args = ['stubgen'] + cfg.get('args', [])
        cfg.setdefault('packages', [pkg.name] if pkg.is_package else [])
        for p in cfg['packages']:
            args += ['-p', p]
        cfg.setdefault('modules', [pkg.name] if not pkg.is_package else [])
        for m in cfg['modules']:
            args += ['-m', m]
        args += cfg.get('files', [])
        # Add output folder argument if not already specified in cfg['args']
        if 'args' not in cfg or not ({'-o', '--output'} & set(cfg['args'])):
            args += ['-o', str(paths.staging_dir)]
        env = os.environ.copy()
        env.setdefault('MYPY_CACHE_DIR', str(paths.temp_dir))
        # Call mypy stubgen in a subprocess
        self.runner.run(args, cwd=pkg.path.parent, check=True, env=env)

    # --- Misc helper functions -----------------------------------------------

    @staticmethod
    def get_os_name():
        return {
            "Linux": "linux",
            "Windows": "windows",
            "Darwin": "mac",
        }[platform.system()]

    @staticmethod
    def print_config_verbose(cfg):
        from . import __version__
        print("\npy-build-cmake (" + __version__ + ")")
        print("options")
        print("================================")
        print("module:")
        pprint(cfg.module)
        print("editable:")
        pprint(cfg.editable)
        print("sdist:")
        pprint(cfg.sdist)
        print("cmake:")
        pprint(cfg.cmake)
        print("stubgen:")
        pprint(cfg.stubgen)
        print("cross:")
        pprint(cfg.cross)
        print("================================\n")

    @staticmethod
    def normalize_version(version):
        from distlib.version import NormalizedVersion
        norm_version = str(NormalizedVersion(version))
        return norm_version

    @staticmethod
    def convert_abi_tag(abi_tag: str, cmake_cfg: Optional[dict]):
        """Set the ABI tag to 'none' or 'abi3', depending on the config options
        specified by the user."""
        if not cmake_cfg:
            return 'none'
        elif cmake_cfg['abi'] == 'auto':
            return abi_tag
        elif cmake_cfg['abi'] == 'none':
            return 'none'
        elif cmake_cfg['abi'] == 'abi3':
            # Only use abi3 if we're actually building for CPython
            m = re.match(r"^cp(\d+).*$", abi_tag)
            if m and int(m[1]) >= cmake_cfg['abi3_minimum_cpython_version']:
                return 'abi3'
            return abi_tag
        else:
            assert False, "Unsupported abi"

    @staticmethod
    def convert_wheel_tags(tags, cfg):
        """Apply convert_abi_tag to each of the abi tags."""
        assert cfg.cmake
        tags = copy(tags)
        cmake_cfg, _ = _BuildBackend.get_cmake_configs(cfg)
        cvt_abi = lambda tag: _BuildBackend.convert_abi_tag(tag, cmake_cfg)
        tags['abi'] = list(map(cvt_abi, tags['abi']))
        if 'none' in tags['abi']:
            tags['pyver'] = ['py3']
        return tags

    @staticmethod
    def is_pure(cfg):
        """Check if the package is a pure-Python package without platform-
        specific binaries."""
        if not cfg.cmake:
            return True
        cmake_cfg, _ = _BuildBackend.get_cmake_configs(cfg)
        return cmake_cfg['pure_python']

    @staticmethod
    def get_native_tags():
        """Get the PEP 425 tags for the current platform."""
        from .tags import get_python_tag, get_abi_tag, get_platform_tag
        return {
            'pyver': [get_python_tag()],
            'abi': [get_abi_tag()],
            'arch': [get_platform_tag()],
        }

    @staticmethod
    def get_cross_tags(crosscfg):
        """Get the PEP 425 tags to use when cross-compiling."""
        tags = _BuildBackend.get_native_tags()
        if 'implementation' in crosscfg and 'version' in crosscfg:
            tags['pyver'] = [crosscfg['implementation'] + crosscfg['version']]
        if 'abi' in crosscfg:
            tags['abi'] = [crosscfg['abi']]
        if 'arch' in crosscfg:
            tags['arch'] = [crosscfg['arch']]
        return tags

    @staticmethod
    def get_build_config_name(cross_cfg):
        """Get a string representing the Python version, ABI and architecture,
        used to name the build folder so builds for different versions don't
        interfere."""
        if cross_cfg:
            tags = _BuildBackend.get_cross_tags(cross_cfg)
        else:
            tags = _BuildBackend.get_native_tags()
        return '-'.join(map(lambda x: x[0], tags.values()))

    @staticmethod
    def needs_cross_native_build(cfg):
        return cfg.cross and 'copy_from_native_build' in cfg.cross

    @staticmethod
    def iter_files(stagedir):
        """Iterate over the files contained in the given folder.

        Yields absolute paths - caller may want to make them relative.
        Excludes any __pycache__ and *.pyc files."""

        # https://github.com/pypa/flit/blob/a4524758604107bde8c77b5816612edb76a604aa/flit_core/flit_core/common.py#L73

        def _include(path):
            name = os.path.basename(path)
            return name != '__pycache__' and not name.endswith('.pyc')

        # Ensure we sort all files and directories so the order is stable
        for dirpath, dirs, files in os.walk(str(stagedir)):
            for file in sorted(files):
                full_path = os.path.join(dirpath, file)
                if _include(full_path):
                    yield full_path

            dirs[:] = [d for d in sorted(dirs) if _include(d)]

    # --- Helper functions for finding programs like CMake --------------------

    @staticmethod
    def check_cmake_program(cfg: config.Config, deps: List[str],
                            runner: CommandRunner):
        assert cfg.cmake
        # Do we need to perform a native build?
        native = not cfg.cross or _BuildBackend.needs_cross_native_build(cfg)
        native_cfg = cfg.cmake[_BuildBackend.get_os_name()] if native else {}
        # Do we need to perform a cross build?
        cross = cfg.cross
        cross_cfg = cfg.cmake.get('cross', {})
        # Find the strictest version requirement
        min_cmake_ver = max(
            _CMAKE_MINIMUM_REQUIRED,
            NormalizedVersion(native_cfg.get('minimum_version', '0.0')),
            NormalizedVersion(cross_cfg.get('minimum_version', '0.0')),
        )
        # If CMake in PATH doesn't work or is too old, add it as a build
        # requirement
        if not runner.check_program_version('cmake', min_cmake_ver, "CMake"):
            deps.append("cmake>=" + str(min_cmake_ver))

        # Check if we need Ninja
        cfgs = []
        if native: cfgs.append(native_cfg)
        if cross: cfgs.append(cross_cfg)
        # Do any of the configs require Ninja as a generator?
        needs_ninja = lambda c: 'ninja' in c.get('generator', '').lower()
        need_ninja = any(map(needs_ninja, cfgs))
        if need_ninja:
            # If so, check if a working version exists in the PATH, otherwise,
            # add it as a build requirement
            if not runner.check_program_version('ninja', None, "Ninja"):
                deps.append("ninja")

    @staticmethod
    def check_stubgen_program(deps: List[str], runner: CommandRunner):
        if not runner.check_program_version('stubgen', None, None, False):
            deps.append("mypy")


_BACKEND = _BuildBackend()
get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
get_requires_for_build_editable = _BACKEND.get_requires_for_build_editable
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist
build_editable = _BACKEND.build_editable
