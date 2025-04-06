"""
distlib.wheel doesn't always return the correct tags, and packaging.tags
returns all tags supported by the interpreter, not the tags that should be used
for the generated wheels. Therefore the only option here is to write our own
(kind of hacky) functions based on packaging.tags.
"""

from __future__ import annotations

import sys
import sysconfig
from importlib.machinery import EXTENSION_SUFFIXES

from ..common.util import platform_to_platform_tag

_INTERPRETER_SHORT_NAMES: dict[str, str] = {
    "python": "py",
    "cpython": "cp",
    "pypy": "pp",
    "ironpython": "ip",
    "jython": "jy",
}


def get_interpreter_name() -> str:
    name = sys.implementation.name
    return _INTERPRETER_SHORT_NAMES.get(name) or name


def get_interpreter_version() -> str:
    return "".join(map(str, sys.version_info[:2]))


def get_cpython_interpreter() -> str:
    return f"cp{get_interpreter_version()}"


def get_abi_flags() -> str:
    """
    https://github.com/pypa/packaging/blob/917612f5774571a99902b5fe04d06099b9e8b667/packaging/tags.py#L135
    https://github.com/pypa/packaging/blob/e624d8edfaa28865de7b5a7da8bd59fd410e5331/src/packaging/tags.py#L164-L165
    """
    py_version = sys.version_info[:2]
    threading = debug = pymalloc = ""
    with_debug = sysconfig.get_config_var("Py_DEBUG")
    has_refcount = hasattr(sys, "gettotalrefcount")
    # Windows doesn't set Py_DEBUG, so checking for support of debug-compiled
    # extension modules is the best option.
    # https://github.com/pypa/pip/issues/3383#issuecomment-173267692
    has_ext = "_d.pyd" in EXTENSION_SUFFIXES
    if with_debug or (with_debug is None and (has_refcount or has_ext)):
        debug = "d"
    if py_version >= (3, 13) and sysconfig.get_config_var("Py_GIL_DISABLED"):
        threading = "t"
    if py_version < (3, 8):
        with_pymalloc = sysconfig.get_config_var("WITH_PYMALLOC")
        if with_pymalloc or with_pymalloc is None:
            pymalloc = "m"
    return f"{threading}{debug}{pymalloc}"  # tdm


def get_cpython_abi() -> str:
    """
    Get the ABI string for CPython, e.g. cp37m.
    """
    return f"{get_cpython_interpreter()}{get_abi_flags()}"


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
