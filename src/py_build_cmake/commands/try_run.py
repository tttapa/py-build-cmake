from __future__ import annotations

from typing import Any

from distlib.version import NormalizedVersion  # type: ignore[import-untyped]

from ..common import CMAKE_MINIMUM_REQUIRED, Config
from ..common.platform import BuildPlatformInfo
from .cmd_runner import CommandRunner


def check_cmake_program(
    plat: BuildPlatformInfo, cfg: Config, deps: list[str], runner: CommandRunner
):
    assert cfg.cmake
    # Do we need to perform a native build?
    native = not cfg.cross
    native_cfg = cfg.cmake.get(plat.os_name, {}) if native else {}
    # Do we need to perform a cross build?
    cross = cfg.cross
    cross_cfg = cfg.cmake.get("cross", {})
    cfgs: list[dict[str, Any]] = []
    if native:
        cfgs.append(native_cfg)
    if cross:
        cfgs.append(cross_cfg)
    # Find the strictest version requirement
    min_cmake_ver = max(
        NormalizedVersion(CMAKE_MINIMUM_REQUIRED),
        NormalizedVersion(CMAKE_MINIMUM_REQUIRED),  # deliberate, for empty case
        *(
            NormalizedVersion(v.get("minimum_version", "0.0"))
            for c in cfgs
            for v in c.values()
        ),
    )
    # If CMake in PATH doesn't work or is too old, add it as a build
    # requirement
    if not runner.check_program_version("cmake", min_cmake_ver, "CMake"):
        deps.append("cmake>=" + str(min_cmake_ver))

    # Do any of the configs require Ninja as a generator?
    need_ninja = any(
        "ninja" in v.get("generator", "").lower() for c in cfgs for v in c.values()
    )
    if need_ninja and not runner.check_program_version("ninja", None, "Ninja"):
        # If so, check if a working version exists in the PATH, otherwise,
        # add it as a build requirement
        deps.append("ninja")


def check_stubgen_program(deps: list[str], runner: CommandRunner):
    if not runner.check_program_version("stubgen", None, None, False):
        # we need https://github.com/python/mypy/pull/14722
        deps.append("mypy>=1.4.0")
