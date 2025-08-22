from __future__ import annotations

import logging
import os
import re
import subprocess as sp
import sysconfig
from typing import Any

from ...common import ConfigError
from ...common.platform import BuildPlatformInfo
from ...config.options.config_option import MultiConfigOption
from ...config.options.list import ListOption
from ..options.string import StringOption
from ..options.value_reference import ValueReference

logger = logging.getLogger(__name__)


def _get_emcc_version():
    result = sp.run(["emcc", "-v"], stderr=sp.PIPE, text=True, check=True)
    m = re.search(r"emcc \([^)]+\) ([\d\.]+)", result.stderr)
    if not m:
        msg = "Failed to determine Emscripten emcc version:\n"
        msg += result.stderr
        raise RuntimeError(msg)
    return m.group(1)


_COMPILERS = {"c": "emcc", "cpp": "em++"}
_BINUTILS = {  # use the em-prefixed binutils programs
    f"CMAKE_{t.upper()}": f"em{t}" for t in ("ar", "nm", "ranlib", "strip")
}
_NO_BINUTILS = {  # otherwise CMake sets these to /usr/bin/objcopy etc.
    f"CMAKE_{t.upper()}": "FALSE"
    for t in ("objcopy", "objdump", "readelf", "addr2line")
}


def cross_compile_pyodide(plat: BuildPlatformInfo, config: ValueReference):
    """Update the configuration to include a cross-compilation configuration
    for Pyodide. In an ideal world, this would just involve setting the Wheel
    tags and passing a single toolchain file to CMake, but unfortunately, the
    current pyodide build workflow involves a lot of environment variables."""
    logger.info("PYODIDE was specified. Automatically enabling cross-compilation.")
    # Prepare cross-compilation config
    assert not config.is_value_set("cross")
    all = MultiConfigOption.default_index
    cross_cfg: dict[str, Any] = {"os": "pyodide"}
    if config.is_value_set("cmake"):
        cross_cfg["cmake"] = {all: {"env": {}, "options": {}}}
    if config.is_value_set("conan"):
        cross_cfg["conan"] = {all: {"profile_host": ListOption(clear=True)}}
        cross_cfg["_conan"] = {
            "settings": [
                "arch=wasm",
                "compiler=emcc",
                "compiler.version=" + _get_emcc_version(),
                "compiler.libcxx=libc++",
            ],
            "conf": [
                "tools.gnu:host_triplet=wasm32-unknown-emscripten",
                "tools.build.cross_building:can_run=False",
                # https://github.com/pybind/pybind11/blob/v2.13.6/tools/pybind11Common.cmake#L78-L102
                "tools.cmake.cmaketoolchain:extra_variables*={'_pybind11_no_exceptions': 'On'}",
                f"tools.cmake.cmaketoolchain:extra_variables*={_BINUTILS!r}",
                f"tools.cmake.cmaketoolchain:extra_variables*={_NO_BINUTILS!r}",
                f"tools.build:compiler_executables={_COMPILERS!r}",
            ],
            "buildenv": [
                "CC=emcc",
                "CXX=em++",
                "AR=emar",
                "NM=emnm",
                "RANLIB=emranlib",
                "STRIP=emstrip",
            ],
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
    if config.is_value_set("cmake"):
        cross_cfg["cmake"][all]["env"]["SETUPTOOLS_EXT_SUFFIX"] = setuptools_ext

    # Check Emscripten toolchain file
    # TODO: this is a hack. CMake older than 3.21 does not support setting the
    #       default toolchain file through an environment variable, so in that
    #       case we do need to set it on the command line. However, this breaks
    #       the use of Conan toolchain files that may be specified by the user,
    #       so we need an escape hatch to disable this.
    if not os.getenv("_PY_BUILD_CMAKE_PYODIDE_NO_TOOLCHAIN_FILE"):
        if "CMAKE_TOOLCHAIN_FILE" not in os.environ:
            logger.warning(
                "CMAKE_TOOLCHAIN_FILE environment variable not set. This may "
                "cause issues when building for WASM outside of the Emscripten SDK."
            )
        else:
            cross_cfg["toolchain_file"] = os.getenv("CMAKE_TOOLCHAIN_FILE")

    # Enable cross-compilation
    config.set_value("cross", cross_cfg)


def _determine_pyodide_python_version(plat: BuildPlatformInfo) -> tuple[str, ...]:
    py_version = os.getenv("PYVERSION")
    if not py_version:
        py_version = plat.python_version
        logger.warning(
            "Pyodide PYVERSION environment variable was not set. "
            "Using native interpreter version instead: %s.",
            py_version,
        )
    py_version_tup = tuple(py_version.split("."))
    if len(py_version_tup) < 2:
        msg = "Invalid value for Pyodide PYVERSION"
        raise ConfigError(msg)
    return py_version_tup


def _determine_pyodide_host_platform() -> str:
    host_plat = os.getenv("_PYTHON_HOST_PLATFORM")
    if not host_plat:
        msg = "Pyodide _PYTHON_HOST_PLATFORM environment variable missing"
        raise ConfigError(msg)
    if "emscripten" not in host_plat:
        msg = "Pyodide _PYTHON_HOST_PLATFORM environment variable invalid"
        raise ConfigError(msg)
    return host_plat


def _determine_pyodide_soabi() -> tuple[str, str | None]:
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
    if not (config.is_value_set("cmake") or config.is_value_set("conan")):
        logger.warning(
            "CMake configuration was empty, "
            "so I'm ignoring the PYODIDE environment variable"
        )
        return
    cross_compile_pyodide(plat, config)
