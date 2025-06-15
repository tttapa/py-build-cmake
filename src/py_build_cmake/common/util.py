from __future__ import annotations

import re
import sys
from typing import Sequence


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
