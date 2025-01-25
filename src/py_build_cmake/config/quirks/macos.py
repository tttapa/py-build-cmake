from __future__ import annotations

import logging
import os
import platform
import re
import sys
from typing import Any

from distlib.util import (  # type: ignore[import-untyped]
    get_platform as get_platform_dashes,
)

from ...common.util import (
    archflags_to_platform_tag,
    platform_to_platform_tag,
)
from ...config.options.config_option import MultiConfigOption
from ..options.cmake_opt import CMakeOption
from ..options.config_path import ConfPath
from ..options.string import StringOption
from ..options.value_reference import ValueReference

logger = logging.getLogger(__name__)


def cross_compile_mac(config: ValueReference, archs):
    """Update the configuration to include a cross-compilation configuration
    that builds for the given architectures."""
    logger.info(
        "ARCHFLAGS was specified. Automatically enabling cross-compilation for %s (native platform: %s)",
        ", ".join(archs),
        platform.machine(),
    )
    assert not config.is_value_set("cross")
    all = MultiConfigOption.default_index
    options = {
        "CMAKE_SYSTEM_NAME": CMakeOption.create("Darwin", "STRING"),
        "CMAKE_OSX_ARCHITECTURES": CMakeOption.create(archs, "STRING"),
    }
    cross_cfg: dict[str, Any] = {
        "os": "mac",
        "cmake": {all: {"options": options}},
    }
    plat_tag = archflags_to_platform_tag(archs)
    if plat_tag:
        cross_arch = get_platform_dashes().split("-")
        cross_arch[-1] = plat_tag
        cross_cfg["arch"] = StringOption.create(
            platform_to_platform_tag("_".join(cross_arch))
        )
    if sys.implementation.name == "cpython":
        version = "".join(map(str, sys.version_info[:2]))
        abi = getattr(sys, "abiflags", "")
        cross_cfg["cmake"][all]["env"] = {
            "SETUPTOOLS_EXT_SUFFIX": StringOption.create(
                f".cpython-{version}{abi}-darwin.so"
            )
        }
    config.set_value("cross", cross_cfg)


def config_quirks_mac(config: ValueReference):
    """Sets CMAKE_OSX_ARCHITECTURES if $ENV{ARCHFLAGS} is set
    on macOS. This ensures compatibility with cibuildwheel. If the interpreter
    architecture is not in the ARCHFLAGS, also enables cross-compilation."""
    archflags = os.getenv("ARCHFLAGS")
    if not archflags:
        return
    archs = list(re.findall(r"-arch +(\S+)", archflags))
    if not archs:
        logger.warning(
            "ARCHFLAGS was set, but its value was not valid, so I'm ignoring it"
        )
        return
    if config.is_value_set("cross"):
        logger.warning(
            "Cross-compilation configuration was not empty, so I'm ignoring ARCHFLAGS"
        )
        return
    if not config.is_value_set("cmake"):
        logger.warning("CMake configuration was empty, so I'm ignoring ARCHFLAGS")
        return
    if platform.machine() not in archs:
        cross_compile_mac(config, archs)
    else:
        logger.info(
            "ARCHFLAGS was set, adding CMAKE_OSX_ARCHITECTURES to cmake.options (%s, native platform: %s)",
            ", ".join(archs),
            platform.machine(),
        )
        all = MultiConfigOption.default_index
        cmake_pth = ConfPath(("cmake", all))
        config.set_value_default(cmake_pth, {})
        config.set_value_default(cmake_pth.join("options"), {})
        config.set_value_default(
            cmake_pth.join("options").join("CMAKE_OSX_ARCHITECTURES"),
            CMakeOption.create(archs, "STRING"),
        )
