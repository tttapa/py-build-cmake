from __future__ import annotations

import logging
import os
import re
import sysconfig
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Generator

from distlib.version import NormalizedVersion  # type: ignore[import-untyped]

from .. import __version__
from ..common import PackageInfo
from ..common.platform import BuildPlatformInfo
from ..common.util import (
    python_version_int_to_py_limited_api_value,
    python_version_int_to_tuple,
)
from ..config.environment import substitute_environment_options
from .cmd_runner import CommandRunner

logger = logging.getLogger(__name__)


@dataclass
class CMakeSettings:
    working_dir: Path
    source_path: Path
    build_path: Path
    os: str
    find_python: bool
    find_python3: bool
    find_python_build_artifacts_prefix: str | None
    find_python3_build_artifacts_prefix: str | None
    minimum_required: str
    generator_platform: str | None
    command: Path = Path("cmake")


@dataclass
class CMakeConfigureSettings:
    environment: dict
    build_type: str | None
    options: dict[str, str]
    args: list[str]
    preset: str | None
    generator: str | None
    make_program: Path | None
    cross_compiling: bool
    toolchain_file: Path | None
    python_prefix: Path | None
    python_library: Path | None
    python_sabi_library: Path | None
    python_include_dir: Path | None
    python_interpreter_id: str | None
    python_soabi: str | None


@dataclass
class CMakeBuildSettings:
    args: list[str]
    tool_args: list[str]
    presets: list[str]
    configs: list[str]


@dataclass
class CMakeInstallSettings:
    args: list[str]
    configs: list[str]
    components: list[str]
    prefix: Path | None


@dataclass
class Option:
    name: str
    value: str
    type: str = "STRING"
    description: str = ""


_MACOSX_DEPL_TGT_MSG = (
    "Please set the appropriate value using the MACOSX_DEPLOYMENT_TARGET "
    "environment variable when invoking py-build-cmake. This ensures that the "
    "appropriate Wheel platform tag is used, and that the version is correctly "
    "passed to CMake using the CMAKE_OSX_DEPLOYMENT_TARGET variable.\n"
    "If you're using cibuildwheel, you can add the following option to your "
    "pyproject.toml file:\n\n"
    "    [tool.cibuildwheel.macos.environment]\n"
    '    MACOSX_DEPLOYMENT_TARGET = "11.0"\n'
)


@dataclass
class PackageTags:
    python_tag: list[str]
    abi_tag: list[str]
    limited_api: int | None = None


class CMaker:
    def __init__(
        self,
        plat: BuildPlatformInfo,
        cmake_settings: CMakeSettings,
        conf_settings: CMakeConfigureSettings,
        build_settings: CMakeBuildSettings,
        install_settings: CMakeInstallSettings,
        package_info: PackageInfo,
        runner: CommandRunner,
        package_tags: PackageTags,
    ):
        self.plat = plat
        self.cmake_settings = cmake_settings
        self.conf_settings = conf_settings
        self.build_settings = build_settings
        self.install_settings = install_settings
        self.package_info = package_info
        self.runner = runner
        self.package_tags = package_tags
        self.environment: dict[str, str] | None = None

        env = self.conf_settings.environment
        if env.pop("MACOSX_DEPLOYMENT_TARGET", None) is not None:
            msg = "Setting MACOSX_DEPLOYMENT_TARGET in "
            msg += "[tools.py-build-cmake.cmake.env] is not "
            msg += "supported. Its value will be ignored.\n"
            msg += _MACOSX_DEPL_TGT_MSG
            logger.warning(msg)
        opts = self.conf_settings.options
        if opts.pop("CMAKE_OSX_DEPLOYMENT_TARGET", None) is not None:
            msg = "Setting CMAKE_OSX_DEPLOYMENT_TARGET in "
            msg += "[tools.py-build-cmake.cmake.options] is not "
            msg += "supported. Its value will be ignored.\n"
            msg += _MACOSX_DEPL_TGT_MSG
            logger.warning(msg)

    def run(self, *args, **kwargs):
        return self.runner.run(*args, **kwargs)

    def prepare_environment(self):
        """Copy of the current environment with the variables defined in the
        user's configuration settings."""
        if self.environment is None:
            pbc = "PY_BUILD_CMAKE"
            self.environment = os.environ.copy()
            self.environment[f"{pbc}_VERSION"] = str(__version__)
            self.environment[f"{pbc}_PROJECT_VERSION"] = self.package_info.version
            self.environment[f"{pbc}_PACKAGE_VERSION"] = self.package_info.version
            self.environment[f"{pbc}_PROJECT_NAME"] = self.package_info.norm_name
            self.environment[f"{pbc}_PACKAGE_NAME"] = self.package_info.norm_name
            self.environment[f"{pbc}_IMPORT_NAME"] = self.package_info.module_name
            self.environment[f"{pbc}_MODULE_NAME"] = self.package_info.module_name
            self.environment[f"{pbc}_BINARY_DIR"] = str(self.cmake_settings.build_path)
            if self.install_settings.prefix is not None:
                install_prefix = str(self.install_settings.prefix)
                self.environment[f"{pbc}_INSTALL_PREFIX"] = install_prefix
            if not self.cross_compiling() and self.plat.machine == "Darwin":
                version = self.plat.macos_version_str
                self.environment["MACOSX_DEPLOYMENT_TARGET"] = version
            if self.conf_settings.environment:
                substitute_environment_options(
                    self.environment, self.conf_settings.environment
                )
        return self.environment

    def cross_compiling(self) -> bool:
        return self.conf_settings.cross_compiling

    def get_configure_options_package(self) -> list[Option]:
        """Flags specific to py-build-cmake, useful in the user's CMake scripts."""
        executable = self.plat.executable.as_posix()
        version = self.plat.python_version_info
        release_level = str(version.releaselevel)
        python_tag = ";".join(self.package_tags.python_tag)
        abi_tag = ";".join(self.package_tags.abi_tag)
        options = [
            Option("PY_BUILD_CMAKE_VERSION", str(__version__)),
            Option("PY_BUILD_CMAKE_PYTHON_INTERPRETER", executable, "FILEPATH"),
            Option("PY_BUILD_CMAKE_BUILD_PYTHON_INTERPRETER", executable, "FILEPATH"),
            Option("PY_BUILD_CMAKE_PYTHON_VERSION", self.plat.python_version),
            Option("PY_BUILD_CMAKE_BUILD_PYTHON_VERSION", self.plat.python_version),
            Option("PY_BUILD_CMAKE_PYTHON_VERSION_MAJOR", str(version.major)),
            Option("PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_MAJOR", str(version.major)),
            Option("PY_BUILD_CMAKE_PYTHON_VERSION_MINOR", str(version.minor)),
            Option("PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_MINOR", str(version.minor)),
            Option("PY_BUILD_CMAKE_PYTHON_VERSION_PATCH", str(version.micro)),
            Option("PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_PATCH", str(version.micro)),
            Option("PY_BUILD_CMAKE_PYTHON_RELEASE_LEVEL", release_level),
            Option("PY_BUILD_CMAKE_BUILD_PYTHON_RELEASE_LEVEL", release_level),
            Option("PY_BUILD_CMAKE_PYTHON_ABIFLAGS", self.plat.python_abiflags),
            Option("PY_BUILD_CMAKE_BUILD_PYTHON_ABIFLAGS", self.plat.python_abiflags),
            Option("PY_BUILD_CMAKE_PROJECT_VERSION", self.package_info.version),
            Option("PY_BUILD_CMAKE_PACKAGE_VERSION", self.package_info.version),
            Option("PY_BUILD_CMAKE_PROJECT_NAME", self.package_info.norm_name),
            Option("PY_BUILD_CMAKE_PACKAGE_NAME", self.package_info.norm_name),
            Option("PY_BUILD_CMAKE_IMPORT_NAME", self.package_info.module_name),
            Option("PY_BUILD_CMAKE_MODULE_NAME", self.package_info.module_name),
            Option("PY_BUILD_CMAKE_PACKAGE_PYTHON_TAG", python_tag),
            Option("PY_BUILD_CMAKE_PACKAGE_ABI_TAG", abi_tag),
        ]
        limited_api = self.package_tags.limited_api
        if limited_api:
            limited_api_hex = python_version_int_to_py_limited_api_value(limited_api)
            use_sabi = ".".join(map(str, python_version_int_to_tuple(limited_api)))
            options += [
                Option("PY_BUILD_CMAKE_PACKAGE_LIMITED_API", limited_api_hex),
                Option("PY_BUILD_CMAKE_PACKAGE_USE_SABI", use_sabi),
            ]
        return options

    def get_native_python_prefixes(self) -> str:
        """Get the prefix paths to locate this (native) Python installation in,
        as a semicolon-separated string."""
        pfxs = map(Path.as_posix, self.plat.python_prefixes.values())
        return ";".join(dict.fromkeys(pfxs))  # remove duplicates, preserve order

    def get_native_python_abi_tuple(self):
        cmake_version = self.cmake_settings.minimum_required
        has_t_flag = NormalizedVersion("3.30") <= NormalizedVersion(cmake_version)
        dmu = "dmut" if has_t_flag else "dmu"
        return ";".join("ON" if c in self.plat.python_abiflags else "OFF" for c in dmu)

    def get_native_python_implementation(self) -> str | None:
        return {
            "cpython": "CPython",
            "pypy": "PyPy",
        }.get(self.plat.implementation)

    def get_native_python_hints(self, prefix: str) -> Generator[Option]:
        """FindPython hints and artifacts for this (native) Python installation."""
        # Python_ROOT_DIR is the most important one, because it tells CMake to
        # look in the given directories first. If the ROOT_DIR contains just
        # one version of Python, CMake should locate it correctly. Note that
        # we also set Python_FIND_STRATEGY=LOCATION to make sure that CMake
        # does not select a newer version of Python it found elsewhere. See also
        # https://discourse.cmake.org/t/how-to-force-findpython-to-locate-a-specific-version-of-python-without-specifying-every-last-artifact/13165/5
        yield Option(prefix + "_ROOT", self.get_native_python_prefixes())
        yield Option(prefix + "_ROOT_DIR", self.get_native_python_prefixes())
        # If there are multiple versions of Python installed in the same
        # ROOT_DIR, then CMake could pick up the wrong version (it picks the
        # latest version by default).
        # To prevent this, the most robust solution is to request both the
        # Interpreter and the Development components in the same call to
        # find_package. Since we also set the Python_EXECUTABLE artifact, CMake
        # should pick the correct version of the development files as well (it
        # tries to match them to the given interpreter).
        # If the user is searching for the Development components only, this
        # won't work, though. We therefore set some of CMake's find_package
        # version variables to guide CMake to the correct version. If the user
        # includes version requirements in their find_package call, though, all
        # bets are off ...
        version_info = self.plat.python_version_info
        version_majmin = f"{version_info.major}.{version_info.minor}"
        yield Option(prefix + "_FIND_VERSION_COUNT", "2")
        yield Option(prefix + "_FIND_VERSION_EXACT", "TRUE")
        yield Option(prefix + "_FIND_VERSION", version_majmin)
        yield Option(prefix + "_FIND_VERSION_MAJOR", str(version_info.major))
        yield Option(prefix + "_FIND_VERSION_MINOR", str(version_info.minor))
        # Another hint to help CMake find the correct version of Python. Note
        # that py-build-cmake only supports CPython and PyPy. If you're using
        # an exotic Python implementation, you should set these hints manually.
        impl = self.get_native_python_implementation()
        if impl:
            yield Option(prefix + "_FIND_IMPLEMENTATIONS", impl)
        # Just setting ROOT_DIR is not enough for CMake 3.31.1 to find the PyPy
        # headers using find_package(Python COMPONENTS Development), so we
        # explicitly set the INCLUDE_DIR as well. However, searching for the
        # Development component without Interpreter leaves SOABI unset, so we
        # need to set it explicitly as well.
        # For CPython, CMake seems to be able to locate the headers without
        # explicitly setting Python_INCLUDE_DIR, but it might find the wrong
        # version if searched without the Interpreter component (see above),
        # so we set the INCLUDE_DIR artifact as well.
        if impl in ("CPython", "PyPy"):
            inc = sysconfig.get_path("platinclude")
            if inc:
                yield Option(prefix + "_INCLUDE_DIR", Path(inc).as_posix())
            ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ""
            # This regex was taken from CMake's FindPython module.
            m = re.match(r"^([.-]|_d\.)(.+)(\.(so|pyd))$", ext_suffix)
            if m:
                yield Option(prefix + "_SOABI", m.group(2))
            if self.cmake_settings.os == "windows":
                yield Option(prefix + "_SOSABI", "")
            else:
                yield Option(prefix + "_SOSABI", "abi3")
        # TODO: FIND_ABI seems to confuse CMake
        # yield Option(prefix + "_FIND_ABI", self.get_native_python_abi_tuple())

    def get_cross_python_hints(self, prefix: str) -> Generator[Option]:
        """FindPython hints and artifacts to set when cross-compiling."""
        if self.conf_settings.python_prefix:
            pfx = self.conf_settings.python_prefix.as_posix()
            yield Option(prefix + "_ROOT", pfx, "PATH")
            yield Option(prefix + "_ROOT_DIR", pfx, "PATH")
        if self.conf_settings.python_library:
            lib = self.conf_settings.python_library.as_posix()
            yield Option(prefix + "_LIBRARY", lib, "FILEPATH")
        if self.conf_settings.python_sabi_library:
            lib = self.conf_settings.python_sabi_library.as_posix()
            yield Option(prefix + "_SABI_LIBRARY", lib, "FILEPATH")
        if self.conf_settings.python_include_dir:
            inc = self.conf_settings.python_include_dir.as_posix()
            yield Option(prefix + "_INCLUDE_DIR", inc, "PATH")
        if self.conf_settings.python_interpreter_id:
            id = self.conf_settings.python_interpreter_id
            yield Option(prefix + "_INTERPRETER_ID", id, "STRING")
        if self.conf_settings.python_soabi is not None:
            soabi = self.conf_settings.python_soabi
            yield Option(prefix + "_SOABI", soabi, "STRING")

    def get_configure_options_python(self) -> list[Option]:
        """Flags to help CMake find the right version of Python."""

        def get_opts(prefix, with_exec=True, native=None):
            if with_exec:
                executable = self.plat.executable.as_posix()
                yield Option(prefix + "_EXECUTABLE", executable, "FILEPATH")
            yield Option(prefix + "_FIND_REGISTRY", "NEVER")
            yield Option(prefix + "_FIND_FRAMEWORK", "NEVER")
            yield Option(prefix + "_FIND_STRATEGY", "LOCATION")
            yield Option(prefix + "_FIND_VIRTUALENV", "FIRST")
            if native is None:
                native = not self.cross_compiling()
            if native:
                yield from self.get_native_python_hints(prefix)
            else:
                yield from self.get_cross_python_hints(prefix)

        opts = []
        if self.cmake_settings.find_python:
            pfx = self.cmake_settings.find_python_build_artifacts_prefix
            opts += [*get_opts("Python", with_exec=pfx is None)]
            if pfx is not None:
                opts += [*get_opts("Python" + pfx, with_exec=True, native=True)]
        if self.cmake_settings.find_python3:
            pfx = self.cmake_settings.find_python3_build_artifacts_prefix
            opts += [*get_opts("Python3", with_exec=pfx is None)]
            if pfx is not None:
                opts += [*get_opts("Python3" + pfx, with_exec=True, native=True)]
        return opts

    def get_configure_options_install(self) -> list[Option]:
        prefix = self.install_settings.prefix
        if prefix:
            return [
                Option("CMAKE_INSTALL_PREFIX", prefix.as_posix(), "PATH"),
                Option("CMAKE_FIND_NO_INSTALL_PREFIX", "On", "BOOL"),
            ]
        return []

    def get_configure_options_make(self) -> list[Option]:
        """Sets CMAKE_MAKE_PROGRAM."""
        if self.conf_settings.make_program:
            opt = Option(
                "CMAKE_MAKE_PROGRAM",
                self.conf_settings.make_program.as_posix(),
                "FILEPATH",
            )
            return [opt]
        return []

    def get_configure_options_toolchain(self) -> list[str]:
        """Sets CMAKE_TOOLCHAIN_FILE."""
        opts = []
        if not self.cross_compiling() and self.plat.machine == "Darwin":
            version = self.plat.macos_version_str
            opts += ["CMAKE_OSX_DEPLOYMENT_TARGET:STRING=" + version]
        if self.conf_settings.toolchain_file:
            toolchain = str(self.conf_settings.toolchain_file)
            opts += ["CMAKE_TOOLCHAIN_FILE:FILEPATH=" + toolchain]
        return opts

    def get_configure_options_settings(self) -> list[str]:
        return [k + "=" + v for k, v in self.conf_settings.options.items()]

    def get_configure_options(self) -> list[str]:
        """Get the list of options (-D) passed to the CMake configure step
        through the command line."""
        return (
            self.get_configure_options_toolchain()
            + self.get_configure_options_settings()
        )

    def get_preload_options(self) -> list[Option]:
        """Get the list of options set in the CMake pre-load script (-C)."""
        return (
            self.get_configure_options_package()
            + self.get_configure_options_make()
            + self.get_configure_options_python()
            + self.get_configure_options_install()
        )

    def write_preload_options(self) -> list[str]:
        """Write the options into the CMake pre-load script and return the
        command-line flags that tell CMake to load it."""
        opts = self.get_preload_options()
        if not opts:
            return []

        def fmt_opt(o: Option):
            return (
                f'set({o.name} "{o.value}"'
                f' CACHE {o.type} "{o.description}" FORCE)\n'
            )

        preload_file = self.cmake_settings.build_path / "py-build-cmake-preload.cmake"
        version = self.cmake_settings.minimum_required
        if self.runner.verbose:
            print("Writing CMake pre-load file")
            print(f"{preload_file}")
            print("---------------------------")
            print(f"cmake_minimum_required(VERSION {version})")
            for o in opts:
                print(fmt_opt(o), end="")
            print("---------------------------\n")
        if not self.runner.dry:
            self.cmake_settings.build_path.mkdir(parents=True, exist_ok=True)
            with preload_file.open("w", encoding="utf-8") as f:
                f.write(f"cmake_minimum_required(VERSION {version})\n")
                for o in opts:
                    f.write(fmt_opt(o))
        return ["-C", str(preload_file)]

    def get_cmake_generator_platform(self) -> list[str]:
        """Returns -A <platform> for the Visual Studio generator on Windows."""
        win = self.cmake_settings.os == "windows"
        gen = self.conf_settings.generator
        vs_gen = win and (not gen or gen.lower().startswith("visual studio"))
        cmake_plat = self.cmake_settings.generator_platform
        if vs_gen and cmake_plat:
            return ["-A", cmake_plat]
        return []

    def get_configure_command(self):
        options = self.get_configure_options()
        cmd = [str(self.cmake_settings.command)]
        cmd += ["-S", str(self.cmake_settings.source_path)]
        if self.conf_settings.preset:
            cmd += ["--preset", self.conf_settings.preset]
        if not self.conf_settings.preset or not self.build_settings.presets:
            cmd += ["-B", str(self.cmake_settings.build_path)]
        if self.conf_settings.generator:
            cmd += ["-G", self.conf_settings.generator]
        cmd += self.get_cmake_generator_platform()
        cmd += self.write_preload_options()
        cmd += [f for opt in options for f in ("-D", opt)]
        cmd += self.conf_settings.args
        return cmd

    def get_working_dir(self):
        cwd = self.cmake_settings.working_dir
        return str(cwd) if cwd is not None else None

    def configure(self):
        env = self.prepare_environment()
        cmd = self.get_configure_command()
        cwd = self.get_working_dir()
        self.run(cmd, cwd=cwd, check=True, env=env)

    def get_build_command(self, config, preset):
        cmd = [str(self.cmake_settings.command), "--build"]
        if preset is not None:
            cmd += ["--preset", preset]
        else:
            cmd += [str(self.cmake_settings.build_path)]
        if config is not None:
            cmd += ["--config", config]
        if self.build_settings.args:
            cmd += self.build_settings.args
        if self.build_settings.tool_args:
            cmd += ["--", *self.build_settings.tool_args]
        return cmd

    def get_build_commands(self):
        presets = self.build_settings.presets or [None]
        configs = self.build_settings.configs or [None]
        for preset, config in product(presets, configs):
            yield self.get_build_command(config, preset)

    def build(self):
        env = self.prepare_environment()
        cwd = self.get_working_dir()
        for cmd in self.get_build_commands():
            self.run(cmd, cwd=cwd, check=True, env=env)

    def get_install_command(self, config):
        for component in self.install_settings.components:
            cmd = [str(self.cmake_settings.command), "--install"]
            cmd += [str(self.cmake_settings.build_path)]
            if self.install_settings.prefix:
                cmd += ["--prefix", str(self.install_settings.prefix)]
            if config is not None:
                cmd += ["--config", config]
            if component:
                cmd += ["--component", component]
            if self.install_settings.args:
                cmd += self.install_settings.args
            yield cmd

    def get_install_commands(self):
        for config in self.install_settings.configs or [None]:
            yield from self.get_install_command(config)

    def install(self):
        env = self.prepare_environment()
        cwd = self.get_working_dir()
        for cmd in self.get_install_commands():
            self.run(cmd, cwd=cwd, check=True, env=env)
