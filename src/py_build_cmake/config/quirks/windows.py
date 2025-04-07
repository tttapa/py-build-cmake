from __future__ import annotations

import configparser
import logging
import os
from pathlib import Path

from ...common.platform import BuildPlatformInfo
from ...common.util import (
    platform_to_platform_tag,
    python_sysconfig_platform_to_cmake_platform_win,
    python_sysconfig_platform_to_cmake_processor_win,
)
from ...config.options.config_option import MultiConfigOption
from ..options.cmake_opt import CMakeOption
from ..options.string import StringOption
from ..options.value_reference import ValueReference

logger = logging.getLogger(__name__)


def get_python_lib(
    plat: BuildPlatformInfo, library_dirs: str | list[str] | None, stable: bool
) -> Path | None:
    """Return the path the the first python<major><minor>.lib or
    python<major>.lib file in any of the library_dirs.
    Returns None if no such file exists.
    It only looks for libraries with the same ABI as specified by plat.abiflags.
    """
    if library_dirs is None:
        return None
    if isinstance(library_dirs, str):
        library_dirs = [library_dirs]

    def possible_locations():
        # TODO: can we always assume that cibw uses a native interpreter with
        #       the same ABI as the target when cross-compiling?
        v = plat.python_version_info
        x = "" if stable else v.minor
        t = "t" if "t" in plat.python_abiflags else ""
        d = "_d" if "d" in plat.python_abiflags else ""
        py3xlib = lambda p: Path(p) / f"python{v.major}{x}{t}{d}.lib"
        yield from map(py3xlib, library_dirs)

    try:
        return next(filter(Path.exists, possible_locations()))
    except StopIteration:
        return None


def configure_python_artifacts(
    plat: BuildPlatformInfo, library_dirs, cross_cfg: dict, stable: bool
):
    python_lib = get_python_lib(plat, library_dirs, stable)
    lib_key = "sabi_library" if stable else "library"
    if python_lib is not None:
        cross_cfg[lib_key] = str(python_lib)
        python_root = python_lib.parent.parent
        if (python_root / "include").exists():
            cross_cfg.setdefault("root", str(python_root))
    else:
        msg = "Python %s was not found in DIST_EXTRA_CONFIG.build_ext.library_dirs: %s."
        logger.warning(msg, lib_key, repr(library_dirs))


def cross_compile_win(
    plat: BuildPlatformInfo,
    config: ValueReference,
    plat_name,
    library_dirs,
    cmake_plat,
    cmake_proc,
):
    """Update the configuration to include a cross-compilation configuration
    that builds for the given platform and processor. If library_dirs contains
    a compatible Python library, it is also included in the configuration, as
    well as the path to the Python installation's root directory, so CMake is
    able to locate Python correctly."""
    msg = "DIST_EXTRA_CONFIG.build_ext specified plat_name that is different from the current platform. "
    msg += "Automatically enabling cross-compilation for %s"
    logger.info(msg, cmake_plat)
    assert not config.is_value_set("cross")
    all = MultiConfigOption.default_index
    options = {
        "CMAKE_SYSTEM_NAME": CMakeOption.create("Windows", "STRING"),
        "CMAKE_SYSTEM_PROCESSOR": CMakeOption.create(cmake_proc, "STRING"),
    }
    cross_cfg = {
        "os": "windows",
        "arch": StringOption.create(platform_to_platform_tag(plat_name)),
        "cmake": {all: {"options": options}},
        "generator_platform": cmake_plat,
    }
    configure_python_artifacts(plat, library_dirs, cross_cfg, stable=False)
    configure_python_artifacts(plat, library_dirs, cross_cfg, stable=True)
    config.set_value("cross", cross_cfg)


def handle_cross_win(
    plat: BuildPlatformInfo,
    config: ValueReference,
    plat_name: str,
    library_dirs: str | list[str] | None,
):
    """Try to configure cross-compilation for the given Windows platform.
    library_dirs should contain the directory with the Python library."""
    plat_proc = (
        python_sysconfig_platform_to_cmake_platform_win(plat_name),
        python_sysconfig_platform_to_cmake_processor_win(plat_name),
    )
    if all(plat_proc):
        cross_compile_win(plat, config, plat_name, library_dirs, *plat_proc)
    else:
        msg = "Cross-compilation setup skipped because the platform %s is unknown"
        logger.warning(msg, plat_name)


def handle_dist_extra_config_win(
    plat: BuildPlatformInfo, config: ValueReference, dist_extra_conf: str
):
    """Read the given distutils configuration file and use it to configure
    cross-compilation if appropriate."""
    distcfg = configparser.ConfigParser()
    distcfg.read(dist_extra_conf)

    library_dirs = distcfg.get("build_ext", "library_dirs", fallback="")
    plat_name = distcfg.get("build_ext", "plat_name", fallback="")

    if plat_name and plat_name != plat.sysconfig_platform:
        handle_cross_win(plat, config, plat_name, library_dirs)


def config_quirks_win(plat: BuildPlatformInfo, config: ValueReference):
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
            msg = "Cross-compilation configuration was not empty, so I'm ignoring DIST_EXTRA_CONFIG"
            logger.warning(msg)
        elif not config.is_value_set("cmake"):
            msg = "CMake configuration was empty, so I'm ignoring DIST_EXTRA_CONFIG"
            logger.warning(msg)
        else:
            handle_dist_extra_config_win(plat, config, dist_extra_conf)
