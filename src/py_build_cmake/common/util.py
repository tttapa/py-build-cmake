import re
from typing import Optional, Sequence, cast, Any
import platform

OSIdentifier: Any
try:
    from typing import Literal

    OSIdentifier = Literal["linux", "windows", "mac"]
except ImportError:
    OSIdentifier = str


def get_os_name() -> OSIdentifier:
    """Get the name of the current platform."""
    osname = {
        "Linux": "linux",
        "Windows": "windows",
        "Darwin": "mac",
    }.get(platform.system())
    if not osname:
        raise ValueError("Unsupported platform")
    return cast(OSIdentifier, osname)


def normalize_name_wheel_pep_427(name):
    """https://www.python.org/dev/peps/pep-0427/#escaping-and-unicode"""
    return re.sub(r"[^\w\d.]+", "_", name, re.UNICODE)


def normalize_name_wheel(name):
    """https://packaging.python.org/en/latest/specifications/binary-distribution-format/#escaping-and-unicode"""
    return re.sub(r"[-_.]+", "_", name).lower()


def python_sysconfig_platform_to_cmake_platform_win(
    plat_name: Optional[str],
) -> Optional[str]:
    """Convert a sysconfig platform string to the corresponding value of
    https://cmake.org/cmake/help/latest/variable/CMAKE_GENERATOR_PLATFORM.html"""
    cmake_platform = {
        None: None,
        "win32": "Win32",
        "win-amd64": "x64",
        "win-arm32": "ARM",
        "win-arm64": "ARM64",
    }.get(plat_name)
    return cmake_platform


def python_sysconfig_platform_to_cmake_processor_win(
    plat_name: Optional[str],
) -> Optional[str]:
    """Convert a sysconfig platform string to the corresponding value of
    https://cmake.org/cmake/help/latest/variable/CMAKE_HOST_SYSTEM_PROCESSOR.html"""
    # The value of %PROCESSOR_ARCHITECTURE% on Windows
    cmake_proc = {
        None: None,
        "win32": "x86",
        "win-amd64": "AMD64",
        "win-arm32": "ARM",
        "win-arm64": "ARM64",
    }.get(plat_name)
    return cmake_proc


def platform_to_platform_tag(plat: str) -> str:
    """https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/#platform-tag"""
    return plat.replace(".", "_").replace("-", "_")


def archflags_to_platform_tag(archflags: Sequence[str]) -> Optional[str]:
    """Convert tuple of CMAKE_OSX_ARCHITECTURES values to the corresponding
    platform tag https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/#platform-tag
    """
    arch = {
        ("arm64", "x86_64"): "universal2",
        ("x86_64",): "x86_64",
        ("arm64",): "arm64",
    }.get(tuple(sorted(archflags)))
    return arch
