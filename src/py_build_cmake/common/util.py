from __future__ import annotations

import platform
import re
import sys
from typing import Sequence, cast

if sys.version_info < (3, 8):
    OSIdentifier = str
else:
    from typing import Literal

    OSIdentifier = Literal["linux", "windows", "mac"]


def get_os_name() -> OSIdentifier:
    """Get the name of the current platform."""
    osname = {
        "Linux": "linux",
        "Windows": "windows",
        "Darwin": "mac",
    }.get(platform.system())
    if not osname:
        msg = "Unsupported platform"
        raise ValueError(msg)
    return cast(OSIdentifier, osname)


def normalize_name_wheel_pep_427(name: str) -> str:
    """https://www.python.org/dev/peps/pep-0427/#escaping-and-unicode"""
    return re.sub(r"[^\w\d.]+", "_", name, flags=re.UNICODE)


def normalize_name_wheel(name: str) -> str:
    """https://packaging.python.org/en/latest/specifications/binary-distribution-format/#escaping-and-unicode"""
    return re.sub(r"[-_.]+", "_", name).lower()


def python_sysconfig_platform_to_cmake_platform_win(
    plat_name: str | None,
) -> str | None:
    """Convert a sysconfig platform string to the corresponding value of
    https://cmake.org/cmake/help/latest/variable/CMAKE_GENERATOR_PLATFORM.html"""
    return {
        None: None,
        "win32": "Win32",
        "win-amd64": "x64",
        "win-arm32": "ARM",
        "win-arm64": "ARM64",
    }.get(plat_name)


def python_sysconfig_platform_to_cmake_processor_win(
    plat_name: str | None,
) -> str | None:
    """Convert a sysconfig platform string to the corresponding value of
    https://cmake.org/cmake/help/latest/variable/CMAKE_HOST_SYSTEM_PROCESSOR.html"""
    # The value of %PROCESSOR_ARCHITECTURE% on Windows
    return {
        None: None,
        "win32": "x86",
        "win-amd64": "AMD64",
        "win-arm32": "ARM",
        "win-arm64": "ARM64",
    }.get(plat_name)


def platform_to_platform_tag(plat: str) -> str:
    """https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/#platform-tag"""
    return plat.replace(".", "_").replace("-", "_")


def archflags_to_platform_tag(archflags: Sequence[str]) -> str | None:
    """Convert tuple of CMAKE_OSX_ARCHITECTURES values to the corresponding
    platform tag https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/#platform-tag
    """
    return {
        ("arm64", "x86_64"): "universal2",
        ("x86_64",): "x86_64",
        ("arm64",): "arm64",
    }.get(tuple(sorted(archflags)))
