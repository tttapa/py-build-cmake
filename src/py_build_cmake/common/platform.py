from __future__ import annotations

import logging
import os
import platform
import re
import sys
import sysconfig
from dataclasses import dataclass, field
from typing import Mapping, cast

from .util import (
    platform_tag_to_archflags,
    python_sysconfig_platform_to_cmake_platform_win,
)

if sys.version_info < (3, 8):
    OSIdentifier = str
else:
    from typing import Literal

    OSIdentifier = Literal["linux", "windows", "mac"]

logger = logging.getLogger(__name__)


@dataclass
class BuildPlatformInfo:
    implementation: str = sys.implementation.name
    sysconfig_platform: str = field(default_factory=sysconfig.get_platform)
    system: str = field(default_factory=platform.system)
    machine: str = field(default_factory=platform.machine)
    archs: tuple[str, ...] | None = None
    macos_version: tuple[int, int] | None = None
    cmake_generator_platform: str | None = None


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


def determine_build_platform_info(  # noqa: PLR0912
    env: Mapping[str, str] | None = None
):
    if env is None:
        env = os.environ
    r = BuildPlatformInfo()

    # Determine CMake generator platform (i.e. whether to use Visual Studio to
    # build for x86 or AMD64)
    if r.system == "Windows":
        r.cmake_generator_platform = python_sysconfig_platform_to_cmake_platform_win(
            r.sysconfig_platform
        )

    if r.system == "Darwin":
        # Check for ARCHFLAGS on macOS
        archflags = env.get("ARCHFLAGS")
        if archflags:
            r.archs = tuple(re.findall(r"-arch +(\S+)", archflags))
            if not r.archs:
                logger.warning(
                    "The ARCHFLAGS environment variable was set, "
                    "but its value is not valid, so I'm ignoring it."
                )
        if not r.archs:
            _, _, machine = platform.mac_ver()
            r.archs = platform_tag_to_archflags(machine)

        # Check for MACOSX_DEPLOYMENT_TARGET on macOS
        target_str = env.get("MACOSX_DEPLOYMENT_TARGET")
        r.macos_version = _check_version_mac(target_str)
        if not r.macos_version:
            if target_str:
                logger.warning(
                    "The MACOSX_DEPLOYMENT_TARGET environment variable was set, "
                    "but its value is not valid, so I'm ignoring it."
                )
            target_str = sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET")
            r.macos_version = _check_version_mac(target_str)
            if target_str:
                if not r.macos_version:
                    logger.warning(
                        "MACOSX_DEPLOYMENT_TARGET sysconfig has an invalid value, so I'm ignoring it"
                    )
                else:
                    logger.info(
                        "The MACOSX_DEPLOYMENT_TARGET environment variable was not set, "
                        "using interpreter default of %s.",
                        target_str,
                    )
        if not r.macos_version:
            target_str, _, _ = platform.mac_ver()
            r.macos_version = _check_version_mac(target_str)
            if r.macos_version:
                logger.info(
                    "MACOSX_DEPLOYMENT_TARGET not set, using system version %s.",
                    target_str,
                )
        if not r.macos_version:
            logger.warning(
                "Unable to determine MACOSX_DEPLOYMENT_TARGET. Please set it as an environment variable."
            )

    return r


def get_os_name(plat: BuildPlatformInfo) -> OSIdentifier:
    """Get the name of the current platform."""
    osname = {
        "Linux": "linux",
        "Windows": "windows",
        "Darwin": "mac",
    }.get(plat.system)
    if not osname:
        msg = "Unsupported platform"
        raise ValueError(msg)
    return cast(OSIdentifier, osname)
