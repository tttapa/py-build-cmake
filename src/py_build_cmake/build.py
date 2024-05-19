from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from distlib.wheel import Wheel  # type: ignore[import-untyped]

from .commands.cmake import (
    CMakeBuildSettings,
    CMakeConfigureSettings,
    CMakeInstallSettings,
    CMaker,
    CMakeSettings,
)
from .commands.cmd_runner import CommandRunner
from .commands.try_run import check_cmake_program, check_stubgen_program
from .common import (
    BuildPaths,
    ComponentConfig,
    Config,
    ConfigError,
    FormattedErrorMessage,
    Module,
    PackageInfo,
    ProblemInModule,
    format_and_rethrow_exception,
    logformat,
    util,
)
from .config import load as config_load
from .config.dynamic import find_module, update_dynamic_metadata
from .export import editable as export_editable
from .export import metadata as export_metadata
from .export import util as export_util
from .export.editable.build_hook import write_build_hook
from .export.sdist import SdistBuilder
from .export.tags import convert_wheel_tags, get_cross_tags, get_native_tags, is_pure

logger = logging.getLogger(__name__)


class _BuildBackend:
    # --- Constructor ---------------------------------------------------------

    def __init__(self) -> None:
        self.runner: CommandRunner = CommandRunner()

    @property
    def verbose(self):
        return self.runner.verbose

    # --- Methods required by PEP 517 -----------------------------------------

    def get_requires_for_build_wheel(self, config_settings=None):
        """https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-wheel"""
        try:
            self.parse_config_settings(config_settings)

            src_dir = Path().resolve()
            cfg = self.read_config(src_dir, config_settings, self.verbose)
            return self.get_requires_build_project(config_settings, cfg, self.runner)
        except Exception as e:
            format_and_rethrow_exception(e)

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
            format_and_rethrow_exception(e)

    def build_editable(
        self, wheel_directory, config_settings=None, metadata_directory=None
    ):
        """https://www.python.org/dev/peps/pep-0660/#build-editable"""
        try:
            assert metadata_directory is None

            # Parse options
            self.parse_config_settings(config_settings)

            # Build wheel
            with tempfile.TemporaryDirectory() as tmp_build_dir:
                return self.build_wheel_in_dir(
                    wheel_directory, tmp_build_dir, config_settings, editable=True
                )
        except Exception as e:
            format_and_rethrow_exception(e)

    def build_sdist(self, sdist_directory, config_settings=None):
        """https://www.python.org/dev/peps/pep-0517/#build-sdist"""
        try:
            # Parse options
            self.parse_config_settings(config_settings)

            return self.do_build_sdist(sdist_directory, config_settings)
        except Exception as e:
            format_and_rethrow_exception(e)

    # --- Parsing config options and metadata ---------------------------------

    @staticmethod
    def is_verbose_enabled(config_settings: dict | None):
        truthy = lambda x: x.lower() in ("", "1", "true", "yes", "y")
        if config_settings is not None:
            verbose_keys = {"verbose", "--verbose", "V", "-V"}
            verbose_opts = {
                k: v for k, v in config_settings.items() if k in verbose_keys
            }
            if verbose_opts:
                last_val = next(reversed(list(verbose_opts.values())))
                return truthy(last_val)
        env_verbose = os.environ.get("PY_BUILD_CMAKE_VERBOSE")
        if env_verbose is not None:
            return truthy(env_verbose)
        return False

    @staticmethod
    def get_log_level(config_settings: dict | None) -> int:
        def parse_log_level(loglevel: str) -> int:
            numeric_level = getattr(logging, loglevel.upper(), None)
            if isinstance(numeric_level, int):
                return numeric_level
            raise ValueError("Invalid log level: %s" % loglevel)

        if config_settings is not None:
            log_keys = {"loglevel", "--loglevel"}
            log_opts = {k: v for k, v in config_settings.items() if k in log_keys}
            if log_opts:
                last_val = next(reversed(list(log_opts.values())))
                return parse_log_level(last_val)
        env_log = os.environ.get("PY_BUILD_CMAKE_LOGLEVEL")
        if env_log is not None:
            return parse_log_level(env_log)
        return logging.INFO

    def parse_config_settings(self, config_settings: dict | None):
        try:
            level = self.get_log_level(config_settings)
            if "GITHUB_ACTIONS" in os.environ:
                formatter = logformat.GitHubActionsFormatter()
                handler = logging.StreamHandler()
                handler.setFormatter(formatter)
                logging.basicConfig(level=level, handlers=[handler])
            else:
                logging.basicConfig(level=level)
        except ValueError as e:
            logger.error("Invalid log level specified", exc_info=e)
        self.runner.verbose = self.is_verbose_enabled(config_settings)

    @staticmethod
    def get_requires_build_project(
        config_settings: dict | None, cfg: Config, runner: CommandRunner
    ):
        deps: list[str] = []
        # Check if we need CMake
        if cfg.cmake:
            check_cmake_program(cfg, deps, runner)
        if cfg.stubgen:
            check_stubgen_program(deps, runner)
        if runner.verbose:
            print("Dependencies for build:", deps)
        return deps

    # --- Building wheels -----------------------------------------------------

    def build_wheel_in_dir(
        self, wheel_dir, tmp_build_dir, config_settings, editable=False
    ):
        """This is the main function that contains all steps necessary to build
        a complete wheel package, including the CMake builds etc."""

        # Load metadata from the pyproject.toml file
        src_dir = Path().resolve()
        cfg, module = self.read_all_metadata(src_dir, config_settings, self.verbose)
        pkg_info = self.get_pkg_info(cfg, module)
        cmake_cfg = self.get_cmake_config(cfg)

        # Set up all paths
        paths = self.get_default_paths(
            wheel_dir, tmp_build_dir, src_dir, cfg, cmake_cfg
        )

        # Copy the module's Python source files to the temporary folder
        if not editable:
            export_util.copy_pkg_source_to(paths.staging_dir, module)
        else:
            paths = export_editable.do_editable_install(cfg, paths, module)

        # Create dist-info folder
        distinfo_dir = f"{pkg_info.norm_name}-{pkg_info.version}.dist-info"
        distinfo_dir = paths.pkg_staging_dir / distinfo_dir
        distinfo_dir.mkdir(parents=True, exist_ok=True)

        # Write metadata, license and entry points to Wheel's distinfo
        export_metadata.write_metadata(cfg, distinfo_dir)
        export_metadata.write_license_files(cfg, distinfo_dir)
        export_metadata.write_entry_points(cfg, distinfo_dir)

        # Configure, build and install the CMake project
        if cmake_cfg:
            cmaker = self.get_cmaker(
                paths.source_dir,
                paths.build_dir,
                paths.staging_dir,
                cmake_cfg,
                cfg.cross,
                pkg_info,
                runner=self.runner,
            )
            cmaker.configure()
            cmaker.build()
            cmaker.install()

            if editable:
                write_build_hook(cfg, paths.pkg_staging_dir, module, cmaker)

        # Generate .pyi stubs (for the Python files only)
        if cfg.stubgen is not None and not editable:
            self.generate_stubs(paths, module, cfg.stubgen)

        # Create wheel
        return self.create_wheel(paths, cfg, cmake_cfg, pkg_info)

    @staticmethod
    def get_pkg_info(cfg: Config | ComponentConfig, module: Module | None):
        return PackageInfo(
            version=str(cfg.standard_metadata.version),
            package_name=cfg.package_name,
            module_name=module.name if module is not None else "",
        )

    @staticmethod
    def get_default_paths(wheel_dir, tmp_build_dir, src_dir, cfg, cmake_cfg):
        build_cfg_name = _BuildBackend.get_build_config_name(cfg.cross)
        if cmake_cfg:
            path = cmake_cfg["build_path"]
            build_dir = Path(str(path).replace("{build_config}", build_cfg_name))
        else:
            build_dir = src_dir / ".py-build-cmake_cache" / build_cfg_name
        return BuildPaths(
            source_dir=src_dir,
            build_dir=build_dir,
            wheel_dir=Path(wheel_dir),
            temp_dir=Path(tmp_build_dir),
            staging_dir=Path(tmp_build_dir) / "staging",
            pkg_staging_dir=Path(tmp_build_dir) / "staging",
        )

    @staticmethod
    def read_all_metadata(src_dir, config_settings, verbose) -> tuple[Config, Module]:
        cfg = _BuildBackend.read_config(src_dir, config_settings, verbose)
        module = find_module(cfg.module, src_dir)
        modfile = module.full_file
        if cfg.standard_metadata.dynamic:
            if module.is_generated:
                msg = "Dynamic metadata is not supported for generated modules/packages"
                raise ConfigError(msg)
            elif module.is_namespace:
                msg = "Dynamic metadata is not supported for namespace packages"
                raise ConfigError(msg)
        try:
            update_dynamic_metadata(cfg.standard_metadata, modfile)
        except ImportError as e:
            logger.error("Error importing %s for reading metadata", str(modfile))
            msg = (
                "\n"
                "\n"
                f"\t\u274C Error importing {modfile} for reading metadata:\n"
                "\n"
                f"\t\t{e.msg}\n"
                "\n"
            )
            raise FormattedErrorMessage(msg) from e
        except ProblemInModule as e:
            logger.error("Error reading metadata from %s", str(modfile))
            msg = (
                "\n"
                "\n"
                f"\t\u274C Error reading metadata from {modfile}:"
                "\n"
                "\n"
                f"\t\t{e}\n"
                "\n"
            )
            raise FormattedErrorMessage(msg) from e
        return cfg, module

    @staticmethod
    def read_config(src_dir, config_settings, verbose):
        """Read the configuration without the dynamic data."""
        return config_load.read_full_config(
            src_dir / "pyproject.toml", config_settings, verbose
        )

    @staticmethod
    def create_wheel(
        paths: BuildPaths, cfg: Config, cmake_cfg, package_info: PackageInfo
    ):
        """Create a wheel package from the build directory."""
        whl = Wheel()
        whl.name = package_info.norm_name
        whl.version = package_info.version
        pure = is_pure(cmake_cfg)
        libdir = "purelib" if pure else "platlib"
        staging_dir = paths.pkg_staging_dir
        whl_paths = {"prefix": str(staging_dir), libdir: str(staging_dir)}
        whl.dirname = paths.wheel_dir
        if pure:
            tags = {"pyver": ["py3"]}
        elif cfg.cross:
            tags = get_cross_tags(cfg.cross)
            tags = convert_wheel_tags(tags, cmake_cfg)
        else:
            tags = get_native_tags()
            tags = convert_wheel_tags(tags, cmake_cfg)
        wheel_path = whl.build(whl_paths, tags=tags, wheel_version=(1, 0))
        logger.debug("Built Wheel: %s", wheel_path)
        return str(Path(wheel_path).relative_to(paths.wheel_dir))

    @staticmethod
    def get_cmake_config(cfg: Config):
        if not cfg.cmake:
            return None
        if cfg.cross is None:
            return cfg.cmake[util.get_os_name()]
        else:
            return cfg.cmake["cross"]

    # --- Building sdists -----------------------------------------------------

    def do_build_sdist(self, sdist_directory, config_settings):
        # Load metadata
        src_dir = Path().resolve()
        pyproject = src_dir / "pyproject.toml"
        cfg, module = self.read_all_metadata(src_dir, config_settings, self.verbose)
        pkg_info = self.get_pkg_info(cfg, module)

        # Export dist
        extra_files = [pyproject, *cfg.referenced_files]
        sdist_cfg = cfg.sdist["cross" if cfg.cross else util.get_os_name()]
        sdist_builder = SdistBuilder(
            module,
            pkg_info,
            metadata=cfg.standard_metadata,
            cfgdir=src_dir,
            extra_files=extra_files,
            include_patterns=sdist_cfg.get("include_patterns", []),
            exclude_patterns=sdist_cfg.get("exclude_patterns", []),
        )
        sdist_tar = sdist_builder.build(Path(sdist_directory))
        return str(Path(sdist_tar).relative_to(sdist_directory))

    # --- CMake builds --------------------------------------------------------

    @staticmethod
    def get_cmaker(
        source_dir: Path,
        build_dir: Path,
        install_dir: Path | None,
        cmake_cfg: dict,
        cross_cfg: dict | None,
        package_info: PackageInfo,
        **kwargs,
    ):
        # Optionally include the cross-compilation settings
        if cross_cfg:
            cross_compiling = True

            def cvt_path(x):
                if x is None:
                    return None
                assert isinstance(x, (Path, str))
                return Path(x)

            cross_opts = {
                "toolchain_file": cvt_path(cross_cfg.get("toolchain_file")),
                "python_prefix": cvt_path(cross_cfg.get("prefix")),
                "python_library": cvt_path(cross_cfg.get("library")),
                "python_include_dir": cvt_path(cross_cfg.get("include_dir")),
            }
        else:
            cross_compiling = False
            cross_opts = {
                "toolchain_file": None,
                "python_prefix": None,
                "python_library": None,
                "python_include_dir": None,
            }

        # Add some CMake configure options
        options = cmake_cfg.get("options", {})
        btype = cmake_cfg.get("build_type")
        if btype:  # -D CMAKE_BUILD_TYPE={type}
            options["CMAKE_BUILD_TYPE:STRING"] = btype

        # CMake options
        return CMaker(
            cmake_settings=CMakeSettings(
                working_dir=source_dir,
                source_path=Path(cmake_cfg["source_path"]),
                build_path=build_dir,
                os=util.get_os_name(),
                find_python=bool(cmake_cfg["find_python"]),
                find_python3=bool(cmake_cfg["find_python3"]),
                minimum_required=cmake_cfg["minimum_version"],
                command=Path("cmake"),
            ),
            conf_settings=CMakeConfigureSettings(
                environment=cmake_cfg.get("env", {}),
                build_type=cmake_cfg.get("build_type"),
                options=options,
                args=cmake_cfg.get("args", []),
                preset=cmake_cfg.get("preset"),
                generator=cmake_cfg.get("generator"),
                cross_compiling=cross_compiling,
                **cross_opts,
            ),
            build_settings=CMakeBuildSettings(
                args=cmake_cfg["build_args"],
                tool_args=cmake_cfg["build_tool_args"],
                presets=cmake_cfg.get("build_presets", []),
                configs=cmake_cfg.get("config", []),
            ),
            install_settings=CMakeInstallSettings(
                args=cmake_cfg["install_args"],
                configs=cmake_cfg.get("config", []),
                components=cmake_cfg.get("install_components", []),
                prefix=install_dir,
            ),
            package_info=package_info,
            **kwargs,
        )

    # --- Generate stubs ------------------------------------------------------

    def generate_stubs(self, paths: BuildPaths, module: Module, cfg: dict[str, Any]):
        """Generate stubs (.pyi) using mypy stubgen."""
        stubs_dir = paths.temp_dir / "stubs"
        args = ["stubgen", *cfg.get("args", [])]
        is_package = module.is_package
        cfg.setdefault("packages", [module.name] if is_package else [])
        for p in cfg["packages"]:
            args += ["-p", p]
        cfg.setdefault("modules", [module.name] if not is_package else [])
        for m in cfg["modules"]:
            args += ["-m", m]
        args += cfg.get("files", [])
        # Add output folder argument if not already specified in cfg['args']
        if "args" not in cfg or not ({"-o", "--output"} & set(cfg["args"])):
            args += ["-o", str(stubs_dir)]
        # Add search path argument if not already specified in cfg['args']
        if "args" not in cfg or "--search-path" not in cfg["args"]:
            args += ["--search-path", str(paths.staging_dir)]
        env = os.environ.copy()
        env.setdefault("MYPY_CACHE_DIR", str(paths.temp_dir))
        # Call mypy stubgen in a subprocess
        self.runner.run(args, cwd=paths.staging_dir, check=True, env=env)
        # Copy the stubs to the staging folder (careful not to overwrite
        # existing stubs generated by CMake)
        self.copy_stubs(stubs_dir, paths)

    def copy_stubs(self, stubs_dir: Path, paths: BuildPaths):
        dest = paths.staging_dir

        def stubs_already_exists(dest_path: Path):
            # We don't want to replace existing .pyi files.
            dest_pyi = dest_path.with_suffix(".pyi")
            if dest_pyi.exists():
                return True
            # If a directory with the same name already exists, we only
            # want to copy our .pyi file if the directory does not contain
            # an __init__.pyi file.
            dest_dir = dest_path.with_suffix("")
            dest_dir_init = dest_dir / "__init__.pyi"
            return dest_dir.is_dir() and dest_dir_init.exists()

        def handle_file(root_path: Path, f: str):
            rel_path = root_path.relative_to(stubs_dir)
            src_path = root_path / f
            dest_path = dest / rel_path / f
            if not stubs_already_exists(dest_path):
                logger.debug("Copying generated stub  %s -> %s", src_path, dest_path)
                shutil.move(str(src_path), str(dest_path))
            else:
                logger.info(
                    "Not copying generated stub file %s because a .pyi "
                    "file for the same module already exists",
                    rel_path / f,
                )

        def handle_dir(root_path: Path, d: str) -> bool:
            rel_path = root_path.relative_to(stubs_dir)
            src_path = root_path / d
            dest_path = dest / rel_path / d
            dest_pyi = dest_path.with_suffix(".pyi")
            # If the destination already has stubs for this (sub)module
            # in a .pyi file, adding the folder as well would only cause
            # confusion. Ignore the new folder and keep the existing
            # .pyi file. Don't recurse into the folder either.
            if dest_pyi.exists():
                logger.info(
                    "Not copying generated stub directory %s because a "
                    ".pyi file for the same module already exists",
                    rel_path / d,
                )
                return False
            # If there's already a folder with the same name, simply recurse
            # into it.
            if dest_path.exists():
                if dest_path.is_dir():
                    return True
                logger.debug(
                    "Not copying generated stub directory %s because a "
                    "file with the same name already exists",
                    rel_path / d,
                )
                return False
            # If there's neither a .pyi file nor a folder with the same
            # name, we can safely move our folder to the destination, and
            # there's no need to recurse any further.
            logger.debug("Copying generated stubs %s -> %s", src_path, dest_path)
            shutil.move(str(src_path), str(dest_path))
            return False

        for root, dirs, files in os.walk(stubs_dir):
            root_path = Path(root)
            is_pyi = lambda f: Path(f).suffix == ".pyi"
            for f in filter(is_pyi, files):
                handle_file(root_path, f)
            dirs[:] = [d for d in dirs if handle_dir(root_path, d)]

    # --- Misc helper functions -----------------------------------------------

    @staticmethod
    def get_build_config_name(cross_cfg):
        """Get a string representing the Python version, ABI and architecture,
        used to name the build folder so builds for different versions don't
        interfere."""
        tags = get_cross_tags(cross_cfg) if cross_cfg else get_native_tags()
        return "-".join(x[0] for x in tags.values())


_BACKEND = _BuildBackend()
get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
get_requires_for_build_editable = _BACKEND.get_requires_for_build_editable
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist
build_editable = _BACKEND.build_editable
