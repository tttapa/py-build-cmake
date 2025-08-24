from __future__ import annotations

import logging
import re
import sysconfig
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from distlib.version import NormalizedVersion  # type: ignore[import-untyped]

from .. import __version__
from ..common import PackageInfo
from ..common.platform import BuildPlatformInfo
from ..common.util import (
    python_version_int_to_py_limited_api_value,
    python_version_int_to_tuple,
)
from .cmd_runner import CommandRunner

logger = logging.getLogger(__name__)


@dataclass
class PythonSettings:
    prefix: Path | None
    library: Path | None
    sabi_library: Path | None
    include_dir: Path | None
    interpreter_id: str | None
    soabi: str | None
    find_python: bool
    find_python3: bool
    find_python_build_artifacts_prefix: str | None
    find_python3_build_artifacts_prefix: str | None
    # If set, always passes hints for the native Python interpreter to CMake,
    # even when cross-compiling. Useful for universal Python installations on
    # macOS.
    force_native: bool


@dataclass
class PackageTags:
    python_tag: list[str]
    abi_tag: list[str]
    limited_api: int | None = None


@dataclass
class Option:
    """Represents a CMake command line option (using the -D flag) or a cache
    variable."""

    name: str
    value: str
    type: str = "STRING"
    description: str = ""

    def cli_key(self):
        cli = self.name
        if self.type:
            cli += f":{self.type}"
        return cli

    def to_cli_string(self):
        return f"{self.cli_key()}={self.value}"

    def to_preload_set(self, force=True):
        force_ = " FORCE" if force else ""
        return (
            f'set({self.name} "{self.value}"'
            f' CACHE {self.type or "STRING"} "{self.description}"{force_})\n'
        )


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


class Builder(ABC):

    def __init__(
        self,
        plat: BuildPlatformInfo,
        package_info: PackageInfo,
        package_tags: PackageTags,
        python_settings: PythonSettings,
        runner: CommandRunner,
    ) -> None:
        self.plat = plat
        self.package_info = package_info
        self.package_tags = package_tags
        self.python_settings = python_settings
        self.runner = runner

    @abstractmethod
    def get_working_dir(self) -> Path: ...

    @abstractmethod
    def get_build_environment(self) -> Mapping[str, str]: ...

    @abstractmethod
    def configure(self) -> None: ...

    @abstractmethod
    def get_build_commands(self) -> Iterable[str | list[str]]: ...

    @abstractmethod
    def build(self) -> None: ...

    @abstractmethod
    def get_install_commands(self) -> Iterable[str | list[str]]: ...

    @abstractmethod
    def install(self) -> None: ...

    @abstractmethod
    def cross_compiling(self) -> bool: ...

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

    def get_env_vars_package(self):
        pbc = "PY_BUILD_CMAKE"
        return {
            f"{pbc}_VERSION": str(__version__),
            f"{pbc}_PROJECT_VERSION": self.package_info.version,
            f"{pbc}_PACKAGE_VERSION": self.package_info.version,
            f"{pbc}_PROJECT_NAME": self.package_info.norm_name,
            f"{pbc}_PACKAGE_NAME": self.package_info.norm_name,
            f"{pbc}_IMPORT_NAME": self.package_info.module_name,
            f"{pbc}_MODULE_NAME": self.package_info.module_name,
        }

    def get_native_python_prefixes(self) -> str:
        """Get the prefix paths to locate this (native) Python installation in,
        as a semicolon-separated string."""
        pfxs = map(Path.as_posix, self.plat.python_prefixes.values())
        return ";".join(dict.fromkeys(pfxs))  # remove duplicates, preserve order

    def get_native_python_implementation(self) -> str | None:
        return {
            "cpython": "CPython",
            "pypy": "PyPy",
        }.get(self.plat.implementation)

    def get_common_python_hints(self, prefix, with_exec):
        if with_exec:
            executable = self.plat.executable.as_posix()
            yield Option(prefix + "_EXECUTABLE", executable, "FILEPATH")
        yield Option(prefix + "_FIND_REGISTRY", "NEVER")
        yield Option(prefix + "_FIND_FRAMEWORK", "NEVER")
        yield Option(prefix + "_FIND_STRATEGY", "LOCATION")
        yield Option(prefix + "_FIND_VIRTUALENV", "FIRST")

    @abstractmethod
    def get_native_python_abi_tuple(self) -> str: ...

    def _get_native_python_abi_tuple(self, cmake_version):
        has_t_flag = NormalizedVersion("3.30") <= NormalizedVersion(cmake_version)
        dmu = "dmut" if has_t_flag else "dmu"
        return ";".join("ON" if c in self.plat.python_abiflags else "OFF" for c in dmu)

    def get_native_python_hints(self, prefix: str, with_exec: bool) -> Iterable[Option]:
        """FindPython hints and artifacts for this (native) Python installation."""
        yield from self.get_common_python_hints(prefix, with_exec=with_exec)
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
            if self.plat.os_name == "windows":
                yield Option(prefix + "_SOSABI", "")
            else:
                yield Option(prefix + "_SOSABI", "abi3")
        # TODO: FIND_ABI seems to confuse CMake
        # yield Option(prefix + "_FIND_ABI", self.get_native_python_abi_tuple())

    def get_cross_python_hints(self, prefix: str, with_exec: bool) -> Iterable[Option]:
        """FindPython hints and artifacts to set when cross-compiling."""
        yield from self.get_common_python_hints(prefix, with_exec=with_exec)
        if self.python_settings.prefix:
            pfx = self.python_settings.prefix.as_posix()
            yield Option(prefix + "_ROOT", pfx, "PATH")
            yield Option(prefix + "_ROOT_DIR", pfx, "PATH")
        if self.python_settings.library:
            lib = self.python_settings.library.as_posix()
            yield Option(prefix + "_LIBRARY", lib, "FILEPATH")
        if self.python_settings.sabi_library:
            lib = self.python_settings.sabi_library.as_posix()
            yield Option(prefix + "_SABI_LIBRARY", lib, "FILEPATH")
        if self.python_settings.include_dir:
            inc = self.python_settings.include_dir.as_posix()
            yield Option(prefix + "_INCLUDE_DIR", inc, "PATH")
        if self.python_settings.interpreter_id:
            id = self.python_settings.interpreter_id
            yield Option(prefix + "_INTERPRETER_ID", id, "STRING")
        if self.python_settings.soabi is not None:
            soabi = self.python_settings.soabi
            yield Option(prefix + "_SOABI", soabi, "STRING")

    def get_configure_options_python(self, native=None) -> list[Option]:
        """Flags to help CMake find the right version of Python."""
        if native is None:
            native = not self.cross_compiling() or self.python_settings.force_native

        def get_opts(prefix, with_exec, native):
            if native:
                yield from self.get_native_python_hints(prefix, with_exec=with_exec)
            else:
                yield from self.get_cross_python_hints(prefix, with_exec=with_exec)

        opts = []
        if self.python_settings.find_python:
            pfx = self.python_settings.find_python_build_artifacts_prefix
            opts += [*get_opts("Python", with_exec=pfx is None, native=native)]
            if pfx is not None:
                opts += [*get_opts("Python" + pfx, with_exec=True, native=True)]
        if self.python_settings.find_python3:
            pfx = self.python_settings.find_python3_build_artifacts_prefix
            opts += [*get_opts("Python3", with_exec=pfx is None, native=native)]
            if pfx is not None:
                opts += [*get_opts("Python3" + pfx, with_exec=True, native=True)]
        return opts

    def check_environment(self, env: dict[str, Any]):
        if env.pop("MACOSX_DEPLOYMENT_TARGET", None) is not None:
            msg = "Setting MACOSX_DEPLOYMENT_TARGET in "
            msg += "[tools.py-build-cmake...env] is not "
            msg += "supported. Its value will be ignored.\n"
            msg += _MACOSX_DEPL_TGT_MSG
            logger.warning(msg)

    def check_cmake_options(self, opts: dict[str, Any]):
        if opts.pop("CMAKE_OSX_DEPLOYMENT_TARGET", None) is not None:
            msg = "Setting CMAKE_OSX_DEPLOYMENT_TARGET in "
            msg += "[tools.py-build-cmake...options] is not "
            msg += "supported. Its value will be ignored.\n"
            msg += _MACOSX_DEPL_TGT_MSG
            logger.warning(msg)


class BuilderConfig(ABC):

    @abstractmethod
    def get_builder(
        self,
        source_dir: Path,
        install_dir: Path | None,
        cross_cfg: dict | None,
        wheel_cfg: dict,
        package_info: PackageInfo,
        runner: CommandRunner,
    ) -> Builder: ...
