from __future__ import annotations

from distlib.version import NormalizedVersion  # type: ignore[import-untyped]

from ..common import CMAKE_MINIMUM_REQUIRED
from ..common.platform import BuildPlatformInfo
from .builder import BuilderConfig
from .cmd_runner import CommandRunner


def check_cmake_program(
    plat: BuildPlatformInfo,
    builders: dict[int, BuilderConfig],
    deps: list[str],
    runner: CommandRunner,
):
    # Find the strictest version requirement
    min_cmake_ver = max(
        NormalizedVersion(CMAKE_MINIMUM_REQUIRED),
        NormalizedVersion(CMAKE_MINIMUM_REQUIRED),  # deliberate, for empty case
        *(
            NormalizedVersion(version)
            for v in builders.values()
            if (version := v.get_minimum_cmake_version()) is not None
        ),
    )
    # If CMake in PATH doesn't work or is too old, add it as a build
    # requirement
    if not runner.check_program_version("cmake", min_cmake_ver, "CMake"):
        deps.append("cmake>=" + str(min_cmake_ver))

    # Do any of the configs require Ninja as a generator?
    need_ninja = any(v.requires_ninja() for v in builders.values())
    if need_ninja and not runner.check_program_version("ninja", None, "Ninja"):
        # If so, check if a working version exists in the PATH, otherwise,
        # add it as a build requirement
        deps.append("ninja")
