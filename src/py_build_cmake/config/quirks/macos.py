from __future__ import annotations

import logging
from typing import Any

from ...common.platform import BuildPlatformInfo
from ...config.options.config_option import MultiConfigOption
from ..options.cmake_opt import CMakeOption
from ..options.config_path import ConfPath
from ..options.string import StringOption
from ..options.value_reference import ValueReference

logger = logging.getLogger(__name__)


def cross_compile_mac(plat: BuildPlatformInfo, config: ValueReference):
    """Update the configuration to include a cross-compilation configuration
    that builds for the given architectures."""
    assert plat.archs is not None
    assert plat.macos_version is not None
    assert not config.is_value_set("cross")
    logger.info(
        "ARCHFLAGS was specified. Automatically enabling cross-compilation for %s (native platform: %s)",
        ", ".join(plat.archs),
        plat.machine,
    )
    all = MultiConfigOption.default_index
    macos_version = plat.macos_version_str
    options = {
        "CMAKE_SYSTEM_NAME": CMakeOption.create("Darwin", "STRING"),
        "CMAKE_OSX_ARCHITECTURES": CMakeOption.create(list(plat.archs), "STRING"),
        "CMAKE_OSX_DEPLOYMENT_TARGET": CMakeOption.create(macos_version, "STRING"),
    }
    env = {"MACOSX_DEPLOYMENT_TARGET": macos_version}
    cross_cfg: dict[str, Any] = {
        "os": "mac",
        "cmake": {all: {"options": options, "env": env}},
    }
    cross_cfg["arch"] = StringOption.create(plat.platform_tag)
    # The SETUPTOOLS_EXT_SUFFIX variable is used by e.g. pybind11
    if plat.implementation == "cpython":
        version = f"{plat.python_version_info.major}{plat.python_version_info.minor}"
        abi = plat.python_abiflags
        cross_cfg["cmake"][all]["env"] = {
            "SETUPTOOLS_EXT_SUFFIX": StringOption.create(
                f".cpython-{version}{abi}-darwin.so"
            )
        }
    config.set_value("cross", cross_cfg)


def config_quirks_mac(plat: BuildPlatformInfo, config: ValueReference):
    """Sets CMAKE_OSX_ARCHITECTURES if $ENV{ARCHFLAGS} is set
    on macOS. This ensures compatibility with cibuildwheel. If the interpreter
    architecture is not in the ARCHFLAGS, also enables cross-compilation."""
    if not plat.archs or plat.archs == (plat.machine,):
        return
    if config.is_value_set("cross"):
        logger.warning(
            "Cross-compilation configuration was not empty, so I'm ignoring ARCHFLAGS"
        )
        return
    if not config.is_value_set("cmake"):
        logger.warning("CMake configuration was empty, so I'm ignoring ARCHFLAGS")
        return
    if plat.machine not in plat.archs:
        cross_compile_mac(plat, config)
    else:
        logger.info(
            "ARCHFLAGS was set, adding CMAKE_OSX_ARCHITECTURES to cmake.options (%s, native platform: %s)",
            ", ".join(plat.archs),
            plat.machine,
        )
        all = MultiConfigOption.default_index
        cmake_pth = ConfPath(("cmake", all))
        config.set_value_default(cmake_pth, {})
        config.set_value_default(cmake_pth.join("options"), {})
        config.set_value_default(
            cmake_pth.join("options").join("CMAKE_OSX_ARCHITECTURES"),
            CMakeOption.create(list(plat.archs), "STRING"),
        )
