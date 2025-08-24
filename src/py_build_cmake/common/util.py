from __future__ import annotations

import re
import sys
from typing import Dict, List, Sequence

if sys.version_info < (3, 8):
    OSIdentifier = str
    WheelTags = Dict[str, List[str]]
else:
    from typing import Literal

    OSIdentifier = Literal["linux", "windows", "mac", "pyodide"]
    WheelTags = Dict[Literal["pyver", "abi", "arch"], List[str]]


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


def python_sysconfig_platform_to_conan_arch_win(
    plat_name: str | None,
) -> str | None:
    """Convert a sysconfig platform string to the corresponding value of 'arch'
    https://docs.conan.io/2/reference/config_files/settings.html"""
    return {
        None: None,
        "win32": "x86",
        "win-amd64": "x86_64",
        "win-arm32": "armv7",
        "win-arm64": "armv8",
    }.get(plat_name)


def cmake_processor_to_generator_platform_win(proc: str | None) -> str | None:
    """Convert a processor architecture (%PROCESSOR_ARCHITECTURE%) to the
    corresponding CMAKE_GENERATOR_PLATFORM value for Visual Studio."""
    return {
        None: None,
        "x86": "Win32",
        "AMD64": "x64",
        "ARM": "ARM",
        "ARM64": "ARM64",
    }.get(proc)


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


def platform_tag_to_archflags(plat: str) -> tuple[str, ...] | None:
    """Inverse of archflags_to_platform_tag"""
    return {
        "universal2": ("arm64", "x86_64"),
        "x86_64": ("x86_64",),
        "arm64": ("arm64",),
    }.get(plat)


def python_tag_to_cmake(x: str):
    """Convert a Python tag (e.g. 'pp') or a sys.implementation name (e.g.
    'pypy') to the corresponding value of CMake's Python_INTERPRETER_ID."""
    return {
        "py": "Python",
        "cp": "Python",
        "python": "Python",
        "pp": "PyPy",
        "pypy": "PyPy",
        "ip": "IronPython",
        "ironpython": "IronPython",
        "jy": "Jython",
        "jython": "Jython",
    }.get(x)
    # CMake also supports the values "Anaconda" and "ActivePython", but Anaconda
    # and ActiveState Python interpreters just report "cpython" as their
    # sys.implementation, and they use the same Wheel tags as CPython.


def python_version_int_to_tuple(version: int):
    assert sys.version_info.major < 10
    str_version = str(version)
    maj, min = str_version[0], str_version[1:]
    return int(maj), int(min)


def python_version_int_to_py_limited_api_value(version: int):
    maj, min = python_version_int_to_tuple(version)
    return f"0x{maj:02X}{min:02X}0000"


def os_to_conan_os(os: OSIdentifier):
    return {
        "linux": "Linux",
        "windows": "Windows",
        "mac": "Macos",
        "pyodide": "Emscripten",
    }[os]


def archs_to_conan_arch(archs):
    try:
        return {
            ("x86_64",): "x86_64",
            ("arm64",): "armv8",
            ("arm64", "x86_64"): "armv8|x86_64",
        }[tuple(sorted(archs))]
    except KeyError as e:
        msg = "Invalid value for ARCHFLAGS"
        raise RuntimeError(msg) from e


def processor_to_conan_arch(machine: str) -> str:
    """Convert the value of platform.machine() to the corresponding Conan
    architecture."""
    return {
        "i386": "x86",  # Linux
        "i686": "x86",  # Linux
        "x86_64": "x86_64",  # Linux, macOS
        "armv6l": "armv6",  # Linux
        "armv7l": "armv7hf",  # Linux
        "aarch64": "armv8",  # Linux
        "Win32": "x86",  # Windows
        "x86": "x86",  # Windows
        "x64": "x86_64",  # Windows
        "AMD64": "x86_64",  # Windows
        "ARM": "armv7",  # Windows
        "ARM64": "armv8",  # Windows
        "ARM64EC": "arm64ec",  # Windows
        "arm64": "armv8",  # macOS
        "arm64e": "armv8.3",  # macOS
    }[machine]
