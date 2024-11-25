"""
distlib.wheel doesn't always return the correct tags, and packaging.tags
returns all tags supported by the interpreter, not the tags that should be used
for the generated wheels. Therefore the only option here is to write our own
(kind of hacky) functions based on packaging.tags.
"""

from __future__ import annotations

import os
import platform
import re
import sys
import sysconfig
from importlib.machinery import EXTENSION_SUFFIXES
from typing import Dict, List, Mapping

from distlib.util import (  # type: ignore[import-untyped]
    get_platform as get_platform_dashes,
)
from packaging import tags

from ..common.util import archflags_to_platform_tag, platform_to_platform_tag

_INTERPRETER_SHORT_NAMES: dict[str, str] = {
    "python": "py",
    "cpython": "cp",
    "pypy": "pp",
    "ironpython": "ip",
    "jython": "jy",
}


def get_platform_tag() -> str:
    return platform_to_platform_tag(get_platform_dashes())


def get_interpreter_name() -> str:
    name = sys.implementation.name
    return _INTERPRETER_SHORT_NAMES.get(name) or name


def get_interpreter_version() -> str:
    return "".join(map(str, sys.version_info[:2]))


def get_cpython_interpreter() -> str:
    return f"cp{get_interpreter_version()}"


def get_cpython_abi() -> str:
    """
    Get the ABI string for CPython, e.g. cp37m.

    https://github.com/pypa/packaging/blob/917612f5774571a99902b5fe04d06099b9e8b667/packaging/tags.py#L135
    """
    py_version = sys.version_info[:2]
    debug = pymalloc = ""
    with_debug = sysconfig.get_config_var("Py_DEBUG")
    has_refcount = hasattr(sys, "gettotalrefcount")
    # Windows doesn't set Py_DEBUG, so checking for support of debug-compiled
    # extension modules is the best option.
    # https://github.com/pypa/pip/issues/3383#issuecomment-173267692
    has_ext = "_d.pyd" in EXTENSION_SUFFIXES
    if with_debug or (with_debug is None and (has_refcount or has_ext)):
        debug = "d"
    if py_version < (3, 8):
        with_pymalloc = sysconfig.get_config_var("WITH_PYMALLOC")
        if with_pymalloc or with_pymalloc is None:
            pymalloc = "m"
    return f"{get_cpython_interpreter()}{debug}{pymalloc}"


def get_generic_interpreter() -> str:
    return f"{get_interpreter_name()}{get_interpreter_version()}"


def get_generic_abi() -> str:
    abi = sysconfig.get_config_var("SOABI") or "none"
    return platform_to_platform_tag(abi)


def get_python_tag() -> str:
    if get_interpreter_name() == "cp":
        return get_cpython_interpreter()
    else:
        return get_generic_interpreter()


def get_abi_tag() -> str:
    if get_interpreter_name() == "cp":
        return get_cpython_abi()
    else:
        return get_generic_abi()


def _guess_arch_mac(archflags: str | None) -> str | None:
    """Returns 'arm64', 'x86_64' or 'universal2', depending on the value of the
    ARCHFLAGS environment variable if set. Otherwise returns the architecture
    obtained from platform.mac_ver(). Returns None if ARCHFLAGS was invalid."""
    if archflags:
        archs = list(re.findall(r"-arch +(\S+)", archflags))
    else:
        _, _, arch = platform.mac_ver()
        archs = [arch]
    return archflags_to_platform_tag(archs)


def _guess_version_mac(target: str | None) -> tuple[int, int]:
    """Returns the macOS version set by the MACOSX_DEPLOYMENT_TARGET environment
    variable, otherwise returns the version from platform.mac_ver()."""
    version_str = None
    if target:
        m = re.match(r"^(\d+\.\d+)", target)
        if m:
            version_str = m.group(1)
    if not version_str:
        version_str, _, _ = platform.mac_ver()
    version_parts = version_str.split(".")
    major = int(version_parts[0]) if len(version_parts) > 0 else 0
    minor = int(version_parts[1]) if len(version_parts) > 1 else 0
    return major, minor


def _guess_platform_tag_mac(env: Mapping[str, str] | None = None) -> str | None:
    """Return an appropriate platform tag based on the ARCHFLAGS and
    MACOSX_DEPLOYMENT_TARGET environment variables if set. Returns None if
    neither was set, or if the platform tag could not be determined based on
    their values."""
    if env is None:
        env = os.environ
    archflags = env.get("ARCHFLAGS")
    target = env.get("MACOSX_DEPLOYMENT_TARGET")
    if not (archflags or target):
        return None
    arch = _guess_arch_mac(archflags)
    if not arch:
        return None
    version = _guess_version_mac(target)
    if arch == "arm64":
        version = max(version, (11, 0))  # ARM64 is only supported on 11.0+
    return f"macosx_{version[0]}_{version[1]}_{arch}"


def guess_platform_tag(env=None) -> str:
    if platform.system() == "Darwin":
        plat = _guess_platform_tag_mac(env)
        if plat:
            return plat
    try:
        return next(tags.sys_tags()).platform
    except StopIteration:
        return get_platform_tag()


WheelTags = Dict[str, List[str]]


def get_native_tags(guess=False) -> WheelTags:
    """Get the PEP 425 tags for the current platform."""
    return {
        "pyver": [get_python_tag()],
        "abi": [get_abi_tag()],
        "arch": [guess_platform_tag() if guess else get_platform_tag()],
    }
