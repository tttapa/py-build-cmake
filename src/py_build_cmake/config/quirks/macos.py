from __future__ import annotations

import logging
from typing import Any

from ...common.platform import BuildPlatformInfo
from ...common.util import archs_to_conan_arch
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
    msg = "ARCHFLAGS was specified. Automatically enabling cross-compilation for %s "
    msg += "(native platform: %s)"
    logger.info(msg, ", ".join(plat.archs), plat.machine)
    all = MultiConfigOption.default_index
    macos_version = plat.macos_version_str
    emulator = None
    if plat.archs == "x86_64" and plat.machine == "arm64":
        emulator = ["arch", "-arch", "x86_64"]
        # TODO: Rosetta 2 will be discontinued
    cross_cfg: dict[str, Any] = {
        "arch": StringOption.create(plat.platform_tag),
        "os": "mac",
        "_force_native_python": True,
    }
    # CMake configuration
    if config.is_value_set("cmake"):
        options = {
            "CMAKE_SYSTEM_NAME": CMakeOption.create("Darwin", "STRING"),
            "CMAKE_OSX_ARCHITECTURES": CMakeOption.create(list(plat.archs), "STRING"),
            "CMAKE_OSX_DEPLOYMENT_TARGET": CMakeOption.create(macos_version, "STRING"),
        }
        if emulator:
            options["CMAKE_CROSSCOMPILING_EMULATOR"] = CMakeOption.create(emulator)
        env = {"MACOSX_DEPLOYMENT_TARGET": macos_version}
        cross_cfg["cmake"] = {all: {"options": options, "env": env}}
    # Conan profile
    if config.is_value_set("conan"):
        options = {}
        if emulator:
            options["CMAKE_CROSSCOMPILING_EMULATOR"] = CMakeOption.create(emulator)
        profile = {
            "settings": [
                f"arch={archs_to_conan_arch(plat.archs)}",
                f"os.version={macos_version}",
                # CMAKE_OSX_ARCHITECTURES and CMAKE_OSX_DEPLOYMENT_TARGET are
                # set automatically by Conan based on arch and os.version
            ],
            "conf": [
                "tools.cmake.cmaketoolchain:system_name=Darwin",
            ],
        }
        cross_cfg["conan"] = {
            all: {"cmake": {"options": options}, "_profile_data": profile}
        }
    # The SETUPTOOLS_EXT_SUFFIX variable is used by e.g. pybind11
    if plat.implementation == "cpython":
        # TODO: We assume that cibuildwheel uses consistent Python versions and
        #       ABIs between the build Python and host Python installations.
        version = f"{plat.python_version_info.major}{plat.python_version_info.minor}"
        abi = plat.python_abiflags
        soabi = f"cpython-{version}{abi}-darwin"
        cross_cfg["soabi"] = soabi
        env = {"SETUPTOOLS_EXT_SUFFIX": StringOption.create(f".{soabi}.so")}
        if config.is_value_set("cmake"):
            cross_cfg["cmake"][all]["env"] = env
        if config.is_value_set("conan"):
            cross_cfg["conan"][all]["cmake"]["env"] = env
    config.set_value("cross", cross_cfg)


def config_quirks_mac(plat: BuildPlatformInfo, config: ValueReference):
    """Sets CMAKE_OSX_ARCHITECTURES if $ENV{ARCHFLAGS} is set
    on macOS. This ensures compatibility with cibuildwheel. If the interpreter
    architecture is not in the ARCHFLAGS, also enables cross-compilation."""
    if not plat.archs or plat.archs == (plat.machine,):
        return
    if config.is_value_set("cross"):
        msg = "Cross-compilation configuration was not empty, so I'm ignoring ARCHFLAGS"
        logger.warning(msg)
        return
    if not (config.is_value_set("cmake") or config.is_value_set("conan")):
        logger.warning("CMake configuration was empty, so I'm ignoring ARCHFLAGS")
        return
    if plat.machine not in plat.archs:
        cross_compile_mac(plat, config)
    else:
        msg = "ARCHFLAGS was set, adding CMAKE_OSX_ARCHITECTURES to cmake.options "
        msg += "(%s, native platform: %s)"
        logger.info(msg, ", ".join(plat.archs), plat.machine)
        all = MultiConfigOption.default_index
        if config.is_value_set("cmake"):
            cmake_pth = ConfPath(("cmake", all))
            config.set_value_default(cmake_pth, {})
            config.set_value_default(cmake_pth.join("options"), {})
            config.set_value_default(
                cmake_pth.join("options").join("CMAKE_OSX_ARCHITECTURES"),
                CMakeOption.create(list(plat.archs), "STRING"),
            )
        # Conan case is handled in conan.py
        # TODO: use conan._profile_data
