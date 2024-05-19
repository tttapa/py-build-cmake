from __future__ import annotations

import configparser
import contextlib
import logging
import os
import platform
import re
import sys
import sysconfig
from pathlib import Path
from typing import Any

from distlib.util import (  # type: ignore[import-untyped]
    get_platform as get_platform_dashes,
)

from ..common.util import (
    archflags_to_platform_tag,
    platform_to_platform_tag,
    python_sysconfig_platform_to_cmake_platform_win,
    python_sysconfig_platform_to_cmake_processor_win,
)
from .options.cmake_opt import CMakeOption
from .options.config_path import ConfPath
from .options.value_reference import ValueReference

logger = logging.getLogger(__name__)


def get_python_lib(library_dirs: str | list[str] | None) -> Path | None:
    """Return the path the the first python<major><minor>.lib or
    python<major>.lib file in any of the library_dirs.
    Returns None if no such file exists."""
    if library_dirs is None:
        return None
    if isinstance(library_dirs, str):
        library_dirs = [library_dirs]

    def possible_locations():
        v = sys.version_info
        py3xlib = lambda d: Path(d) / f"python{v.major}{v.minor}.lib"
        py3lib = lambda d: Path(d) / f"python{v.major}.lib"
        yield from map(py3xlib, library_dirs)
        yield from map(py3lib, library_dirs)

    try:
        return next(filter(Path.exists, possible_locations()))
    except StopIteration:
        return None


def cross_compile_win(
    config: ValueReference, plat_name, library_dirs, cmake_plat, cmake_proc
):
    """Update the configuration to include a cross-compilation configuration
    that builds for the given platform and processor. If library_dirs contains
    a compatible Python library, it is also included in the configuration, as
    well as the path to the Python installation's root directory, so CMake is
    able to locate Python correctly."""
    logger.info(
        "DIST_EXTRA_CONFIG.build_ext specified plat_name that is different from the current platform. "
        "Automatically enabling cross-compilation for %s",
        cmake_plat,
    )
    assert not config.is_value_set("cross")
    cross_cfg = {
        "os": "windows",
        "arch": platform_to_platform_tag(plat_name),
        "cmake": {
            "options": {
                "CMAKE_SYSTEM_NAME": CMakeOption.create("Windows", "STRING"),
                "CMAKE_SYSTEM_PROCESSOR": CMakeOption.create(cmake_proc, "STRING"),
                "CMAKE_GENERATOR_PLATFORM": CMakeOption.create(cmake_plat, "STRING"),
            }
        },
    }
    python_lib = get_python_lib(library_dirs)
    if python_lib is not None:
        cross_cfg["library"] = str(python_lib)
        python_root = python_lib.parent.parent
        if (python_root / "include").exists():
            cross_cfg["root"] = str(python_root)
    else:
        logger.warning(
            "Python library was not found in DIST_EXTRA_CONFIG.build_ext.library_dirs."
        )
    config.set_value("cross", cross_cfg)


def handle_cross_win(
    config: ValueReference, plat_name: str, library_dirs: str | list[str] | None
):
    """Try to configure cross-compilation for the given Windows platform.
    library_dirs should contain the directory with the Python library."""
    plat_proc = (
        python_sysconfig_platform_to_cmake_platform_win(plat_name),
        python_sysconfig_platform_to_cmake_processor_win(plat_name),
    )
    if all(plat_proc):
        cross_compile_win(config, plat_name, library_dirs, *plat_proc)
    else:
        logger.warning(
            "Cross-compilation setup skipped because the platform %s is unknown",
            plat_name,
        )


def handle_dist_extra_config_win(config: ValueReference, dist_extra_conf: str):
    """Read the given distutils configuration file and use it to configure
    cross-compilation if appropriate."""
    distcfg = configparser.ConfigParser()
    distcfg.read(dist_extra_conf)

    library_dirs = distcfg.get("build_ext", "library_dirs", fallback="")
    plat_name = distcfg.get("build_ext", "plat_name", fallback="")

    if plat_name and plat_name != sysconfig.get_platform():
        handle_cross_win(config, plat_name, library_dirs)


def config_quirks_win(config: ValueReference):
    """
    Explanation:
    The cibuildwheel tool sets the DIST_EXTRA_CONFIG environment variable when
    cross-compiling. It points to a configuration file that contains the path
    to the correct Python library (.lib), as well as the name of the platform
    to compile for.
    If the user did not specify a custom cross-compilation configuration,
    we will automatically add a minimal cross-compilation configuration that
    points CMake to the right Python library, and that selects the right
    CMake/Visual Studio platform.
    """
    dist_extra_conf = os.getenv("DIST_EXTRA_CONFIG")
    if dist_extra_conf is not None:
        if config.is_value_set("cross"):
            logger.warning(
                "Cross-compilation configuration was not empty, so I'm ignoring DIST_EXTRA_CONFIG"
            )
        elif not config.is_value_set("cmake"):
            logger.warning(
                "CMake configuration was empty, so I'm ignoring DIST_EXTRA_CONFIG"
            )
        else:
            handle_dist_extra_config_win(config, dist_extra_conf)


def cross_compile_mac(config: ValueReference, archs):
    """Update the configuration to include a cross-compilation configuration
    that builds for the given architectures."""
    logger.info(
        "ARCHFLAGS was specified. Automatically enabling cross-compilation for %s (native platform: %s)",
        ", ".join(archs),
        platform.machine(),
    )
    assert not config.is_value_set("cross")
    cross_cfg: dict[str, Any] = {
        "os": "mac",
        "cmake": {
            "options": {
                "CMAKE_SYSTEM_NAME": CMakeOption.create("Darwin", "STRING"),
                "CMAKE_OSX_ARCHITECTURES": CMakeOption.create(archs, "STRING"),
            }
        },
    }
    plat_tag = archflags_to_platform_tag(archs)
    if plat_tag:
        cross_arch = get_platform_dashes().split("-")
        cross_arch[-1] = plat_tag
        cross_cfg["arch"] = platform_to_platform_tag("_".join(cross_arch))
    if sys.implementation.name == "cpython":
        version = "".join(map(str, sys.version_info[:2]))
        abi = getattr(sys, "abiflags", "")
        env = cross_cfg["cmake"]["env"] = {}
        env["SETUPTOOLS_EXT_SUFFIX"] = f".cpython-{version}{abi}-darwin.so"
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
        config.set_value_default(ConfPath.from_string("cmake/options"), {})
        config.set_value_default(
            ConfPath.from_string("cmake/options/CMAKE_OSX_ARCHITECTURES"),
            CMakeOption.create(archs, "STRING"),
        )


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
