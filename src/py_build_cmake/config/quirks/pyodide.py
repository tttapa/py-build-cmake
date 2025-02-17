from __future__ import annotations

import logging
import os
import re
import sysconfig
from typing import Any

from ...common import ConfigError
from ...common.platform import BuildPlatformInfo
from ...config.options.config_option import MultiConfigOption
from ..options.cmake_opt import CMakeOption
from ..options.string import StringOption
from ..options.value_reference import ValueReference

logger = logging.getLogger(__name__)


def cross_compile_pyodide(plat: BuildPlatformInfo, config: ValueReference):
    """Update the configuration to include a cross-compilation configuration
    for Pyodide. In an ideal world, this would just involve setting the Wheel
    tags and passing a single toolchain file to CMake, but unfortunately, the
    current pyodide build workflow involves a lot of environment variables."""
    logger.info("PYODIDE was specified. Automatically enabling cross-compilation.")
    # Prepare cross-compilation config
    assert not config.is_value_set("cross")
    all = MultiConfigOption.default_index
    cross_cfg: dict[str, Any] = {
        # "os": "pyodide",  # TODO: add an override section to the config
        "cmake": {all: {"env": {}, "options": {}}},
    }

    # Determine Python version
    py_version = _determine_pyodide_python_version(plat)
    # Determine interpreter and ABI
    cross_cfg["implementation"] = StringOption.create("cp")
    cross_cfg["abi"] = StringOption.create("cp" + "".join(py_version[:2]))

    # Determine the platform
    host_plat = _determine_pyodide_host_platform()
    cross_cfg["arch"] = StringOption.create(host_plat)

    # Set FindPython hints
    cross_cfg["include_dir"] = os.getenv("PYTHONINCLUDE")
    cross_cfg["prefix"] = os.getenv("PYODIDE_ROOT")

    # Determine the extension suffix
    ext_suffix, soabi = _determine_pyodide_soabi()
    if soabi is not None:
        cross_cfg["soabi"] = StringOption.create(soabi)

    # The SETUPTOOLS_EXT_SUFFIX variable is used by e.g. pybind11
    setuptools_ext = StringOption.create(ext_suffix)
    cross_cfg["cmake"][all]["env"]["SETUPTOOLS_EXT_SUFFIX"] = setuptools_ext

    # Set Emscripten toolchain file
    toolchain = os.getenv("CMAKE_TOOLCHAIN_FILE")
    if toolchain:
        cross_cfg["toolchain_file"] = toolchain
    else:
        logger.warning(
            "CMAKE_TOOLCHAIN_FILE environment variable not set. This may "
            "cause issues when building for WASM outside of the Emscripten SDK."
        )

    # By default, CMake locates the build system's strip program, which won't
    # work for Emscripten. By setting strip to False here, we prevent pybind11
    # from trying to use it.
    if "STRIP" not in os.environ:
        strip_opt = CMakeOption.create(False)
        cross_cfg["cmake"][all]["options"]["CMAKE_STRIP"] = strip_opt

    # Enable cross-compilation
    config.set_value("cross", cross_cfg)


def _determine_pyodide_python_version(plat):
    py_version = os.getenv("PYVERSION")
    if not py_version:
        py_version = plat.python_version
        logger.warning(
            "Pyodide PYVERSION environment variable was not set. "
            "Using native interpreter version instead: %s.",
            py_version,
        )
    py_version = py_version.split(".")
    if len(py_version) < 2:
        msg = "Invalid value for Pyodide PYVERSION"
        raise ConfigError(msg)
    return py_version


def _determine_pyodide_host_platform():
    host_plat = os.getenv("_PYTHON_HOST_PLATFORM")
    if not host_plat:
        msg = "Pyodide _PYTHON_HOST_PLATFORM environment variable missing"
        raise ConfigError(msg)
    if "emscripten" not in host_plat:
        msg = "Pyodide _PYTHON_HOST_PLATFORM environment variable invalid"
        raise ConfigError(msg)
    return host_plat


def _determine_pyodide_soabi():
    ext_suffix: str = (
        os.getenv("SETUPTOOLS_EXT_SUFFIX")
        or sysconfig.get_config_var("EXT_SUFFIX")
        or ""
    )
    if "emscripten" not in ext_suffix:
        msg = "Invalid EXT_SUFFIX for Pyodide. "
        msg += "Please set the SETUPTOOLS_EXT_SUFFIX environment variable."
        raise ConfigError(msg)
    # Determine the SOABI
    soabi: str | None = None
    # This regex was taken from CMake's FindPython module.
    m = re.match(r"^([.-]|_d\.)(.+)(\.(so|pyd))$", ext_suffix)
    soabi = m.group(2) if m else sysconfig.get_config_var("SOABI")
    if soabi is not None and "emscripten" not in soabi:
        msg = "Invalid SOABI for Pyodide. "
        msg += "Please set the SETUPTOOLS_EXT_SUFFIX environment variable."
        raise ConfigError(msg)
    if soabi is not None and soabi not in ext_suffix:
        logger.warning(
            "Inconsistent SOABI and EXT_SUFFIX: %s and %s", soabi, ext_suffix
        )
    return ext_suffix, soabi


def config_quirks_pyodide(plat: BuildPlatformInfo, config: ValueReference):
    """Enables cross-compilation for pyodide."""
    if config.is_value_set("cross"):
        logger.warning(
            "Cross-compilation configuration was not empty, "
            "so I'm ignoring the PYODIDE environment variable"
        )
        return
    if not config.is_value_set("cmake"):
        logger.warning(
            "CMake configuration was empty, "
            "so I'm ignoring the PYODIDE environment variable"
        )
        return
    cross_compile_pyodide(plat, config)
