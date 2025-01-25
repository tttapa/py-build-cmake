from __future__ import annotations

import contextlib
import logging
import platform
import sys

from ..options.value_reference import ValueReference
from .macos import config_quirks_mac
from .windows import config_quirks_win

logger = logging.getLogger(__name__)


def config_quirks_pypy(config: ValueReference):
    if sys.version_info < (3, 8):
        with contextlib.suppress(KeyError):
            del config.values["stubgen"]
            logger.info("Mypy is not supported on PyPy <3.8, disabling stubgen")


def config_quirks(config: ValueReference):
    dispatch = {
        "Windows": config_quirks_win,
        "Darwin": config_quirks_mac,
    }.get(platform.system())
    if dispatch is not None:
        dispatch(config)
    dispatch = {
        "pypy": config_quirks_pypy,
    }.get(sys.implementation.name)
    if dispatch is not None:
        dispatch(config)
