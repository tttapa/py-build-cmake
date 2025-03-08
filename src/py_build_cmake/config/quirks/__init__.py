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
    if plat.python_version_info < (3, 8):
        with contextlib.suppress(KeyError):
            del config.values["stubgen"]
            logger.info("Mypy is not supported on PyPy <3.8, disabling stubgen")


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
