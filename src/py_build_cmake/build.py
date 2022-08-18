import platform
from pprint import pprint
import sys
import os
from pathlib import Path
from string import Template
import re
import shutil
import textwrap
from typing import Any, Dict, List, Optional
import tempfile
from subprocess import CalledProcessError, run as sp_run
from glob import glob

from .config import Config

from distlib.version import NormalizedVersion

_CMAKE_MINIMUM_REQUIRED = NormalizedVersion('3.15')


class _BuildBackend(object):

    # --- Constructor ---------------------------------------------------------

    def __init__(self) -> None:
        self.verbose = False

    # --- Methods required by PEP 517 -----------------------------------------

    def get_requires_for_build_wheel(self, config_settings=None):
        """https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-wheel"""
        self.parse_config_settings(config_settings)
        pyproject = Path('pyproject.toml').resolve()
        cfg = self.read_metadata(pyproject, config_settings)
        deps = []
        # Check if we need CMake
        if cfg.cmake:
            self.check_cmake_program(cfg, deps)
        if cfg.stubgen:
            self.check_stubgen_program(cfg, deps)
        if self.verbose:
            print('Dependencies for build:', deps)
        return deps

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
        from flit_core.common import Module, make_metadata
        pyproject = src_dir / 'pyproject.toml'
        cfg = self.read_metadata(pyproject, config_settings)
        import_name = cfg.module['name']
        pkg = Module(import_name, src_dir / cfg.module['directory'])
        metadata = make_metadata(pkg, cfg)
        metadata.version = self.normalize_version(metadata.version)

        # Export dist
        from flit_core.sdist import SdistBuilder
        rel_pyproject = os.path.relpath(pyproject, src_dir)
        extra_files = [str(rel_pyproject)] + cfg.referenced_files
        sdist_cfg = cfg.sdist[self.get_os_name()]
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

    def parse_config_settings(self, config_settings: Optional[Dict]):
        if 'PY_BUILD_CMAKE_VERBOSE' in os.environ:
            self.verbose = True
        if config_settings is None:
            return
        if config_settings.keys() & {'verbose', '--verbose', 'v', '-v'}:
            self.verbose = True

    def read_metadata(self, pyproject, config_settings: Optional[Dict]):
        from .config import read_metadata
        from flit_core.config import ConfigError

        config_settings = config_settings or {}
        try:
            listify = lambda x: x if isinstance(x, list) else [x]
            keys = ['--local', '--cross']
            overrides = {
                key: listify(config_settings.get(key) or [])
                for key in keys
            }
            if self.verbose:
                print("Configuration settings for local and "
                      "cross-compilation overrides:")
                pprint(overrides)
            cfg = read_metadata(pyproject, overrides)
        except ConfigError as e:
            e.args = ("\n"
                      "\n"
                      "\t❌ Error in configuration:\n"
                      "\n"
                      f"\t\t{e}\n"
                      "\n", )
            raise
        if self.verbose:
            self.print_config_verbose(cfg)
        return cfg

    # --- Building wheels -----------------------------------------------------

    def build_wheel_in_dir(self,
                           wheel_directory,
                           tmp_build_dir,
                           config_settings,
                           editable=False):
        """This is the main function that contains all steps necessary to build
        a complete wheel package, including the CMake builds etc."""
        # Set up all paths
        wheel_directory = Path(wheel_directory)
        tmp_build_dir = Path(tmp_build_dir)
        staging_dir = tmp_build_dir / 'staging'
        src_dir = Path().resolve()

        # Load metadata from the pyproject.toml file
        from .config import normalize_name_wheel
        from flit_core.common import Module, make_metadata
        cfg = self.read_metadata(src_dir / 'pyproject.toml', config_settings)
        dist_name = normalize_name_wheel(cfg.metadata['name'])
        import_name = cfg.module['name']
        pkg = Module(import_name, src_dir / cfg.module['directory'])
        metadata = make_metadata(pkg, cfg)
        metadata.version = self.normalize_version(metadata.version)

        # Copy the module's Python source files to the temporary folder
        if not editable:
            self.copy_pkg_source_to(staging_dir, src_dir, pkg)
        else:
            self.write_editable_wrapper(staging_dir, src_dir, pkg)

        # Create dist-info folder
        distinfo = staging_dir / f'{dist_name}-{metadata.version}.dist-info'
        os.makedirs(distinfo, exist_ok=True)

        # Write metadata
        metadata_path = distinfo / 'METADATA'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            metadata.write_metadata_file(f)
        # Write or copy license
        self.write_license_files(cfg.license, src_dir, distinfo)
        # Write entrypoints/scripts
        self.write_entrypoints(distinfo, cfg)

        # Generate .pyi stubs (for the Python files only)
        if cfg.stubgen is not None and not editable:
            self.generate_stubs(tmp_build_dir, staging_dir, pkg, cfg.stubgen)

        # Configure, build and install the CMake project
        if cfg.cmake:
            self.do_native_cross_cmake_build(tmp_build_dir, staging_dir,
                                             src_dir, cfg, metadata, dist_name,
                                             import_name)

        # Create wheel
        whl_name = self.create_wheel(wheel_directory, staging_dir, cfg,
                                     dist_name, metadata.version)
        return whl_name

    def create_wheel(self, wheel_directory, tmp_build_dir, cfg, dist_name,
                     norm_version):
        """Create a wheel package from the build directory."""
        from distlib.wheel import Wheel
        whl = Wheel()
        whl.name = dist_name
        whl.version = norm_version
        pure = not cfg.cmake
        libdir = 'purelib' if pure else 'platlib'
        paths = {'prefix': str(tmp_build_dir), libdir: str(tmp_build_dir)}
        whl.dirname = wheel_directory
        if pure:
            tags = {'pyver': ['py3']}
        elif cfg.cross:
            tags = self.get_cross_tags(cfg.cross)
        else:
            tags = self.get_native_tags()
        wheel_path = whl.build(paths, tags=tags, wheel_version=(1, 0))
        whl_name = os.path.relpath(wheel_path, wheel_directory)
        return whl_name

    def do_native_cross_cmake_build(self, tmp_build_dir, staging_dir, src_dir,
                                    cfg, metadata, dist_name, import_name):
        """If not cross-compiling, just do a regular CMake build+install.
        When cross-compiling, do a cross-build+install (using the provided 
        CMake toolchain file).
        If cfg.cross['copy_from_native_build'] is set, before cross-compiling, 
        first a normal build+install is performed to a separate directory, then
        the cross-build+install is performed, and finally the installed files
        from the native build that match the patterns in
        cfg.cross['copy_from_native_build'] are copied to the installation
        directory of the cross-build for packaging."""
        # When cross-compiling, optionally do a native build first
        native_install_dir = None
        native_cmake_cfg = cfg.cmake[self.get_os_name()]
        if self.needs_cross_native_build(cfg):
            native_install_dir = tmp_build_dir / 'native-install'
            self.run_cmake(src_dir, native_install_dir, metadata,
                           native_cmake_cfg, None, native_install_dir,
                           dist_name, import_name)
        # Then do the actual build
        cmake_cfg = cfg.cmake['cross'] if cfg.cross else native_cmake_cfg
        self.run_cmake(src_dir, staging_dir, metadata, cmake_cfg, cfg.cross,
                       native_install_dir, dist_name, import_name)
        # Finally, move the files from the native build to the staging area
        if native_install_dir:
            self.copy_native_install(staging_dir, native_install_dir,
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

    def copy_pkg_source_to(self, tmp_build_dir, src_dir, pkg):
        """Copy the files of a Python package to the build directory."""
        for mod_file in pkg.iter_files():
            rel_path = os.path.relpath(mod_file, pkg.path.parent)
            dst = tmp_build_dir / rel_path
            os.makedirs(dst.parent, exist_ok=True)
            shutil.copy2(mod_file, dst, follow_symlinks=False)

    def write_license_files(self, license, srcdir: Path, distinfo_dir: Path):
        """Write the LICENSE file from pyproject.toml to the distinfo
        directory."""
        if 'text' in license:
            with (distinfo_dir / 'LICENSE').open('w', encoding='utf-8') as f:
                f.write(license['text'])
        elif 'file' in license:
            shutil.copy2(srcdir / license['file'], distinfo_dir)

    def write_entrypoints(self, distinfo: Path, cfg: Config):
        from flit_core.common import write_entry_points
        with (distinfo / 'entry_points.txt').open('w', encoding='utf-8') as f:
            write_entry_points(cfg.entrypoints, f)

    # --- Editable installs ---------------------------------------------------

    def write_editable_wrapper(self, tmp_build_dir: Path, src_dir: Path, pkg):
        """Write a fake __init__.py file that points to the development 
        folder."""
        tmp_pkg: Path = tmp_build_dir / pkg.name
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
        (tmp_build_dir / f'{pkg.name}.pth').write_text(str(pkg.path.parent))

    # --- Invoking CMake builds -----------------------------------------------

    def run_cmake(self, pkgdir, install_dir, metadata, cmake_cfg, cross_cfg,
                  native_install_dir, dist_name, import_name):
        """Configure, build and install using CMake."""
        # Source and build folders
        srcdir = Path(cmake_cfg.get('source_path', pkgdir)).resolve()
        builddir = pkgdir / '.py-build-cmake_cache'
        builddir = Path(cmake_cfg.get('build_path', builddir))
        if not builddir.is_absolute():
            builddir = pkgdir / builddir
        buildconfig = self.get_build_config_name(cross_cfg)
        builddir = builddir / buildconfig
        builddir = builddir.resolve()
        # Environment variables
        cmake_env = os.environ.copy()
        f = 'env'
        if f in cmake_cfg:
            for k, v in cmake_cfg[f].items():
                cmake_env[k] = Template(v).substitute(cmake_env)

        # Configure
        configure_cmd = [
            'cmake',
            '-B',
            str(builddir),
            '-S',
            str(srcdir),
            '-D',
            'PY_BUILD_CMAKE_PACKAGE_VERSION:STRING=' + metadata.version,
            '-D',
            'PY_BUILD_CMAKE_PACKAGE_NAME:STRING=' + dist_name,
            '-D',
            'PY_BUILD_CMAKE_MODULE_NAME:STRING=' + import_name,
        ]
        if cross_cfg:
            toolchain = (pkgdir / cross_cfg['toolchain_file']).resolve()
            configure_cmd += [
                '-D', 'CMAKE_TOOLCHAIN_FILE:FILEPATH=' + str(toolchain), '-D',
                'Python3_EXECUTABLE:FILEPATH=' + sys.executable
            ]
        else:
            configure_cmd += [
                '-D', 'Python3_EXECUTABLE:FILEPATH=' + sys.executable, '-D',
                'Python3_ROOT_DIR:PATH=' + sys.prefix, '-D',
                'Python3_FIND_REGISTRY=NEVER', '-D',
                'Python3_FIND_STRATEGY=LOCATION'
            ]
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            # https://github.com/pybind/cmake_example/pull/48
            if self.get_os_name() == "mac" and "ARCHFLAGS" in os.environ:
                archs = re.findall(r"-arch (\S+)", os.environ["ARCHFLAGS"])
                if archs:
                    configure_cmd += [
                        '-D',
                        'CMAKE_OSX_ARCHITECTURES={}'.format(";".join(archs)),
                    ]
        if native_install_dir:
            configure_cmd += [
                '-D', 'PY_BUILD_CMAKE_NATIVE_INSTALL_DIR:PATH=' +
                str(native_install_dir)
            ]
        configure_cmd += cmake_cfg.get('args', [])  # User-supplied arguments
        for k, v in cmake_cfg.get('options', {}).items():  # -D {option}={val}
            configure_cmd += ['-D', k + '=' + v]
        btype = cmake_cfg.get('build_type')
        if btype:  # -D CMAKE_BUILD_TYPE={type}
            configure_cmd += ['-D', 'CMAKE_BUILD_TYPE=' + btype]
        gen = cmake_cfg.get('generator')
        if gen:  # -G {generator}
            configure_cmd += ['-G', gen]
        self.run(configure_cmd, check=True, env=cmake_env)

        # Build and install
        if not cmake_cfg.get('config', False):
            self.build_install_cmake(cmake_cfg, builddir, cmake_env,
                                     install_dir, None)
        else:
            for config in cmake_cfg['config']:
                self.build_install_cmake(cmake_cfg, builddir, cmake_env,
                                         install_dir, config)

    def build_install_cmake(self, cmake_cfg, builddir, cmake_env, install_dir,
                            config):
        """Build the CMake project and install it."""
        self.build_cmake(cmake_cfg, builddir, cmake_env, config)
        self.install_cmake(cmake_cfg, builddir, cmake_env, install_dir, config)

    def build_cmake(self, cmake_cfg, builddir, cmake_env, config):
        """Build the CMake project."""
        build_cmd = ['cmake', '--build', str(builddir)]
        build_cmd += cmake_cfg.get('build_args', [])  # User-supplied arguments
        if config:  # --config {config}
            build_cmd += ['--config', config]
        f = 'build_tool_args'
        if f in cmake_cfg:
            build_cmd += ['--'] + cmake_cfg[f]
        self.run(build_cmd, check=True, env=cmake_env)

    def install_cmake(self, cmake_cfg, builddir, cmake_env, install_dir,
                      config):
        """Install the CMake project."""
        for component in cmake_cfg['install_components']:
            install_cmd = [
                'cmake', '--install',
                str(builddir), '--prefix',
                str(install_dir)
            ]
            install_cmd += cmake_cfg.get('install_args', [])
            if config:  # --config {config}
                install_cmd += ['--config', config]
            if component:
                install_cmd += ['--component', component]
            print('Installing component', component or 'all')
            self.run(install_cmd, check=True, env=cmake_env)

    # --- Generate stubs ------------------------------------------------------

    def generate_stubs(self, tmp_build_dir, staging_dir, pkg, cfg: Dict[str,
                                                                        Any]):
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
            args += ['-o', str(staging_dir)]
        env = os.environ.copy()
        env.setdefault('MYPY_CACHE_DIR', str(tmp_build_dir))
        # Call mypy stubgen in a subprocess
        self.run(args, cwd=pkg.path.parent, check=True, env=env)

    # --- Misc helper functions -----------------------------------------------

    @staticmethod
    def get_os_name():
        return {
            "Linux": "linux",
            "Windows": "windows",
            "Darwin": "mac",  # TODO: untested
        }[platform.system()]

    def print_config_verbose(self, cfg):
        print("\npy-build-cmake options")
        print("======================")
        print("module:")
        pprint(cfg.module)
        print("sdist:")
        pprint(cfg.sdist)
        print("cmake:")
        pprint(cfg.cmake)
        print("stubgen:")
        pprint(cfg.stubgen)
        print("cross:")
        pprint(cfg.cross)
        print("======================\n")

    def normalize_version(self, version):
        from distlib.version import NormalizedVersion
        norm_version = str(NormalizedVersion(version))
        return norm_version

    def run(self, *args, **kwargs):
        """Wrapper around subprocess.run that optionally prints the command."""
        if self.verbose:
            pprint([*args])
            pprint(kwargs)
        return sp_run(*args, **kwargs)

    @staticmethod
    def get_cross_tags(crosscfg):
        """Get the PEP 425 tags to use when cross-compiling."""
        return {
            'pyver': [crosscfg['implementation'] + crosscfg['version']],
            'abi': [crosscfg['abi']],
            'arch': [crosscfg['arch']],
        }

    @staticmethod
    def get_native_tags():
        from .tags import get_python_tag, get_abi_tag, get_platform_tag
        return {
            'pyver': [get_python_tag()],
            'abi': [get_abi_tag()],
            'arch': [get_platform_tag()],
        }

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

    def needs_cross_native_build(self, cfg):
        return cfg.cross and 'copy_from_native_build' in cfg.cross

    def iter_files(self, stagedir):
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

    def check_cmake_program(self, cfg: Config, deps: List[str]):
        assert cfg.cmake
        # Do we need to perform a native build?
        native = not cfg.cross or self.needs_cross_native_build(cfg)
        native_cfg = cfg.cmake[self.get_os_name()] if native else {}
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
        if not self.check_program_version('cmake', min_cmake_ver, "CMake"):
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
            if not self.check_program_version('ninja', None, "Ninja"):
                deps.append("ninja")

    def check_stubgen_program(self, cfg: Config, deps: List[str]):
        if not self.check_program_version('stubgen', None, None, False):
            deps.append("mypy")

    def check_program_version(
        self,
        program: str,
        minimum_version: Optional[NormalizedVersion],
        name: Optional[str],
        check_version: bool = True,
    ):
        """Check if there's a new enough version of the given command available
        in PATH."""
        name = name or program
        try:
            # Try running the command
            cmd = [program, '--version'] if check_version else [program, '-h']
            res = self.run(cmd, check=True, capture_output=True)
            # Try finding the version
            if check_version:
                m = re.search(r'\d+(\.\d+){1,}', res.stdout.decode('utf-8'))
                if not m:
                    raise RuntimeError(f"Unexpected {name} version output")
                program_version = NormalizedVersion(m.group(0))
                if self.verbose: print("Found", name, program_version)
                # Check if the version is new enough
                if minimum_version is not None:
                    if program_version < minimum_version:
                        raise RuntimeError(f"{name} too old")
        except CalledProcessError as e:
            if self.verbose:
                print(f'{type(e).__module__}.{type(e).__name__}', e, sep=': ')
                sys.stdout.buffer.write(e.stdout)
                sys.stdout.buffer.write(e.stderr)
            return False
        except Exception as e:
            # If any of that failed, return False
            if self.verbose:
                print(f'{type(e).__module__}.{type(e).__name__}', e, sep=': ')
            return False
        return True


_BACKEND = _BuildBackend()
get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
get_requires_for_build_editable = _BACKEND.get_requires_for_build_editable
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist
build_editable = _BACKEND.build_editable
