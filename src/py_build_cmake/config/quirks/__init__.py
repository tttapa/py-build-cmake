from __future__ import annotations

import contextlib
import logging

from ...common.platform import BuildPlatformInfo
from ..options.value_reference import ValueReference
from .macos import config_quirks_mac
from .pyodide import config_quirks_pyodide
from .windows import config_quirks_win

logger = logging.getLogger(__name__)


def config_quirks_pypy(plat: BuildPlatformInfo, config: ValueReference):
    with contextlib.suppress(KeyError):
        del config.values["stubgen"]
        msg = "ast-serialize and librt (mypy dependencies) do not support "
        msg += "PyPy (https://github.com/python/mypy/issues/21460), "
        msg += "disabling stubgen"
        logger.info(msg)


def config_quirks_free_threaded(plat: BuildPlatformInfo, config: ValueReference):
    with contextlib.suppress(KeyError):
        del config.values["stubgen"]
        msg = "ast-serialize and librt (mypy dependencies) do not support the "
        msg += "free-threaded ABI (https://github.com/python/mypy/issues/21460), "
        msg += "disabling stubgen"
        logger.info(msg)


def config_quirks(plat: BuildPlatformInfo, config: ValueReference):
    dispatch = {
        "windows": config_quirks_win,
        "mac": config_quirks_mac,
        "pyodide": config_quirks_pyodide,
    }.get(plat.os_name)
    if dispatch is not None:
        dispatch(plat, config)
    dispatch = {
        "pypy": config_quirks_pypy,
    }.get(plat.implementation)
    if dispatch is not None:
        dispatch(plat, config)
    if "t" in plat.python_abiflags:
        # TODO: how best to check on Windows?
        config_quirks_free_threaded(plat, config)
