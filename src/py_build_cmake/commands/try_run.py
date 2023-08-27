from __future__ import annotations

from distlib.version import NormalizedVersion

from ..common import Config
from ..common.util import get_os_name
from .cmd_runner import CommandRunner

_CMAKE_MINIMUM_REQUIRED = NormalizedVersion("3.15")


def check_cmake_program(cfg: Config, deps: list[str], runner: CommandRunner):
    assert cfg.cmake
    # Do we need to perform a native build?
    native = not cfg.cross
    native_cfg = cfg.cmake[get_os_name()] if native else {}
    # Do we need to perform a cross build?
    cross = cfg.cross
    cross_cfg = cfg.cmake.get("cross", {})
    # Find the strictest version requirement
    min_cmake_ver = max(
        _CMAKE_MINIMUM_REQUIRED,
        NormalizedVersion(native_cfg.get("minimum_version", "0.0")),
        NormalizedVersion(cross_cfg.get("minimum_version", "0.0")),
    )
    # If CMake in PATH doesn't work or is too old, add it as a build
    # requirement
    if not runner.check_program_version("cmake", min_cmake_ver, "CMake"):
        deps.append("cmake>=" + str(min_cmake_ver))

    # Check if we need Ninja
    cfgs = []
    if native:
        cfgs.append(native_cfg)
    if cross:
        cfgs.append(cross_cfg)

    # Do any of the configs require Ninja as a generator?
    needs_ninja = lambda c: "ninja" in c.get("generator", "").lower()
    need_ninja = any(map(needs_ninja, cfgs))
    if need_ninja and not runner.check_program_version("ninja", None, "Ninja"):
        # If so, check if a working version exists in the PATH, otherwise,
        # add it as a build requirement
        deps.append("ninja")


def check_stubgen_program(deps: list[str], runner: CommandRunner):
    if not runner.check_program_version("stubgen", None, None, False):
        deps.append("mypy")
