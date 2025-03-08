from __future__ import annotations

import logging
import os
import platform
import re
import sys
import sysconfig
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, cast

import packaging.tags

from ..export.native_tags import (
    get_abi_flags as tags_get_abi_flags,
)
from ..export.native_tags import (
    get_abi_tag,
    get_python_tag,
)
from .util import (
    archflags_to_platform_tag,
    platform_tag_to_archflags,
    platform_to_platform_tag,
    python_sysconfig_platform_to_cmake_platform_win,
)

logger = logging.getLogger(__name__)

if sys.version_info < (3, 8):
    OSIdentifier = str
    WheelTags = Dict[str, List[str]]
else:
    from typing import Literal

    OSIdentifier = Literal["linux", "windows", "mac", "pyodide"]
    WheelTags = Dict[Literal["pyver", "abi", "arch"], List[str]]


def _get_python_prefixes():
    return {
        "exec_prefix": Path(sys.exec_prefix),
        "prefix": Path(sys.prefix),
        "base_exec_prefix": Path(sys.base_exec_prefix),
        "base_prefix": Path(sys.base_prefix),
    }


def _get_specific_platform(env: Mapping[str, str] | None = None) -> str:
    """Get the most specific platform for the current interpreter from
    packaging.tags. On Linux, this will include the glibc version, which is not
    the case for sysconfig.platform()."""
    if env is None:
        env = os.environ
    host_plat = env.get("_PYTHON_HOST_PLATFORM")
    if host_plat:
        return platform_to_platform_tag(host_plat)
    try:
        return next(packaging.tags.sys_tags()).platform
    except StopIteration:
        return platform_to_platform_tag(sysconfig.get_platform())


def _get_abi_flags():
    if hasattr(sys, "abiflags"):
        return sys.abiflags
    return tags_get_abi_flags()


@dataclass
class BuildPlatformInfo:
    executable: Path = field(default_factory=lambda: Path(sys.executable))
    implementation: str = sys.implementation.name
    python_version: str = field(default_factory=platform.python_version)
    python_version_info = sys.version_info
    python_abiflags: str = field(default_factory=_get_abi_flags)
    python_prefixes: dict[str, Path] = field(default_factory=_get_python_prefixes)
    sysconfig_platform: str = field(default_factory=sysconfig.get_platform)
    specific_platform_tag: str = field(default_factory=_get_specific_platform)
    python_tag: str = field(default_factory=get_python_tag)
    abi_tag: str = field(default_factory=get_abi_tag)
    system: str = field(default_factory=platform.system)
    machine: str = field(default_factory=platform.machine)
    pyodide: bool = field(default_factory=lambda: os.getenv("PYODIDE") == "1")
    archs: tuple[str, ...] | None = None
    macos_version: tuple[int, int] | None = None
    cmake_generator_platform: str | None = None

    @property
    def macos_version_str(self) -> str:
        assert self.macos_version is not None
        return ".".join(map(str, self.macos_version))

    @property
    def os_name(self) -> OSIdentifier:
        """Get the name of the current platform. For use in file names etc.,
        and consistent with the values in the py-build-cmake configs."""
        if self.pyodide:
            return "pyodide"
        osname = {
            "Linux": "linux",
            "Windows": "windows",
            "Darwin": "mac",
        }.get(self.system)
        if not osname:
            msg = f"Unsupported platform: {self.system}"
            raise ValueError(msg)
        return cast(OSIdentifier, osname)

    @property
    def platform_tag(self) -> str:
        if self.system == "Linux":
            return self._platform_tag_linux()
        elif self.system == "Darwin":
            return self._platform_tag_macos()
        elif self.system == "Windows":
            return self._platform_tag_windows()
        else:
            return platform_to_platform_tag(self.sysconfig_platform)

    def get_native_tags(self, guess=False) -> WheelTags:
        """Get the PEP 425 tags for the current platform."""
        return {
            "pyver": [self.python_tag],
            "abi": [self.abi_tag],
            "arch": [self.specific_platform_tag if guess else self.platform_tag],
        }

    def _platform_tag_linux(self):
        return platform_to_platform_tag(self.sysconfig_platform)

    def _platform_tag_macos(self):
        assert self.archs is not None
        binary_fmt = archflags_to_platform_tag(self.archs)
        if not binary_fmt:
            msg = f"Unable to determine platform tag: {self.archs}. "
            msg += "Please verify the value of ARCHFLAGS."
            raise RuntimeError(msg)
        assert self.macos_version is not None
        # https://github.com/tttapa/py-build-cmake/issues/41
        version = self.macos_version
        if self.archs == ("arm64",):
            version = max(version, (11, 0))  # ARM64 is only supported on 11.0+
        major_version = version[0]
        minor_version = 0 if major_version >= 11 else version[1]
        return f"macosx_{major_version}_{minor_version}_{binary_fmt}"

    def _platform_tag_windows(self):
        return platform_to_platform_tag(self.sysconfig_platform)


def _check_version_mac(target: str | None) -> tuple[int, int] | None:
    """Returns the macOS version given by the target argument if it is valid,
    otherwise returns None."""
    version_str = None
    if target:
        if "." not in target:
            target += ".0"
        m = re.match(r"^(\d+\.\d+)", target)
        if m:
            version_str = m.group(1)
    if not version_str:
        return None
    version_parts = version_str.split(".")
    major = int(version_parts[0]) if len(version_parts) > 0 else 0
    minor = int(version_parts[1]) if len(version_parts) > 1 else 0
    return major, minor


def _determine_macos_version_archs(
    env: Mapping[str, str],
) -> tuple[tuple[int, int], tuple[str, ...]]:
    # Check for ARCHFLAGS on macOS
    archflags = env.get("ARCHFLAGS")
    archs = None
    if archflags:
        archs = tuple(re.findall(r"-arch +(\S+)", archflags))
        if not archs:
            logger.warning(
                "The ARCHFLAGS environment variable was set, "
                "but its value is not valid, so I'm ignoring it."
            )
    if not archs:
        _, _, machine = platform.mac_ver()
        archs = platform_tag_to_archflags(machine)
    if not archs:
        msg = "Unable to determine macOS architecture. Please set the ARCHFLAGS environment variable"
        raise RuntimeError(msg)

    # Check for MACOSX_DEPLOYMENT_TARGET on macOS
    target_str = env.get("MACOSX_DEPLOYMENT_TARGET")
    macos_version = _check_version_mac(target_str)
    if not macos_version:
        if target_str:
            logger.warning(
                "The MACOSX_DEPLOYMENT_TARGET environment variable was set, "
                "but its value is not valid, so I'm ignoring it."
            )
        target_str = sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET")
        macos_version = _check_version_mac(target_str)
        if target_str:
            if not macos_version:
                logger.warning(
                    "MACOSX_DEPLOYMENT_TARGET sysconfig has an invalid value, so I'm ignoring it"
                )
            else:
                logger.info(
                    "The MACOSX_DEPLOYMENT_TARGET environment variable was not set, "
                    "using interpreter default of %s.",
                    target_str,
                )
    if not macos_version:
        target_str, _, _ = platform.mac_ver()
        macos_version = _check_version_mac(target_str)
        if macos_version:
            logger.info(
                "MACOSX_DEPLOYMENT_TARGET not set, using system version %s.",
                target_str,
            )
    if not macos_version:
        msg = "Unable to determine MACOSX_DEPLOYMENT_TARGET. Please set it as an environment variable."
        raise RuntimeError(msg)

    return macos_version, archs


def determine_build_platform_info(env: Mapping[str, str] | None = None, **kwargs):
    if env is None:
        env = os.environ
    kwargs.setdefault("specific_platform_tag", _get_specific_platform(env))
    r = BuildPlatformInfo(**kwargs)

    # Determine CMake generator platform (i.e. whether to use Visual Studio to
    # build for x86 or AMD64)
    if r.system == "Windows":
        r.cmake_generator_platform = python_sysconfig_platform_to_cmake_platform_win(
            r.sysconfig_platform
        )
        if not r.cmake_generator_platform:
            msg = "Unknown platform %s. Not setting CMake generator platform."
            logger.warning(msg, r.sysconfig_platform)

    # For macOS, we need to change the platform tag etc. based on the values of
    # MACOSX_DEPLOYMENT_TARGET and ARCHFLAGS.
    elif r.system == "Darwin":
        r.macos_version, r.archs = _determine_macos_version_archs(env)
        if "_PYTHON_HOST_PLATFORM" in env:
            host_plat = env["_PYTHON_HOST_PLATFORM"]
            if platform_to_platform_tag(host_plat) != r._platform_tag_macos():
                msg = "Computed platform tag (%s) does not match "
                msg += "environment variable _PYTHON_HOST_PLATFORM (%s). "
                msg += "Please make sure that the values of the ARCHFLAGS "
                msg += "and MACOSX_DEPLOYMENT_TARGET variables are consistent "
                msg += "with _PYTHON_HOST_PLATFORM."
                logger.warning(msg, r._platform_tag_macos(), host_plat)
        r.specific_platform_tag = r._platform_tag_macos()

    return r
