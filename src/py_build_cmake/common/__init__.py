from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, Sequence

import pyproject_metadata

logger = logging.getLogger(__name__)

CMAKE_MINIMUM_REQUIRED = "3.15"


class FormattedErrorMessage(Exception):
    """Wrapper exception for any error that already has a nicely formatted
    error message."""


class ConfigError(ValueError):
    """Problem processing the pyproject.toml config"""


class ProblemInModule(ValueError):
    """Problem processing the project's modules"""


class NoDocstringError(ProblemInModule):
    """The module does not contain a docstring that can be used as package
    description."""


class NoVersionError(ProblemInModule):
    """The module does not contain a __version__."""


class InvalidVersion(ProblemInModule):
    """The __version__ is invalid."""


@dataclass
class Module:
    """Describes the location and name of a Python package or module"""

    name: str
    full_path: Path
    base_path: Path
    is_package: bool
    is_namespace: bool
    is_generated: bool = False

    @property
    def prefix(self):
        return self.full_path.parent

    @property
    def full_file(self):
        if self.is_package and not self.is_namespace:
            return self.full_path / "__init__.py"
        else:
            return self.full_path

    def iter_files_abs(self):
        """Iterate over the files contained in this module.
        Yields absolute paths. Excludes any __pycache__ and *.pyc files.
        """
        assert self.is_package or not self.is_namespace

        if self.is_generated:
            # Generated modules/packages don't exist in the source directory
            return

        def _include(s: str | Path):
            p = Path(s)
            return p.name != "__pycache__" and not p.name.endswith(".pyc")

        if self.is_package:
            # Ensure we sort all files and directories so the order is stable
            for dirpath, dirs, files in os.walk(str(self.full_path)):
                for file in sorted(files):
                    filepath = Path(dirpath) / file
                    if _include(filepath):
                        yield filepath
                dirs[:] = filter(_include, sorted(dirs))
        else:
            yield self.full_file


@dataclass
class Config:
    """Describes the metadata and configuration settings for the standard
    build backend."""

    standard_metadata: pyproject_metadata.StandardMetadata
    package_name: str = field(default="")
    module: dict[str, str | bool] = field(default_factory=dict)
    editable: dict[str, dict[str, Any]] = field(default_factory=dict)
    sdist: dict[str, dict[str, Any]] = field(default_factory=dict)
    cmake: dict[str, dict[str, Any]] | None = field(default=None)
    wheel: dict[str, dict[str, Any]] = field(default_factory=dict)
    stubgen: dict[str, Any] | None = field(default=None)
    cross: dict[str, Any] | None = field(default=None)

    @property
    def referenced_files(self) -> list[Path]:
        metadata = self.standard_metadata
        readme, lic = metadata.readme, metadata.license
        res: list[Path] = []
        if isinstance(readme, pyproject_metadata.Readme) and readme.file is not None:
            res += [readme.file]
        if isinstance(lic, pyproject_metadata.License) and lic.file is not None:
            res += [lic.file]
        if metadata.license_files:
            res += metadata.license_files
        return res

    def check(self):
        """Check for any incompatible options."""
        if self.module["namespace"] and any(
            e["mode"] == "wrapper" for e in self.editable.values()
        ):
            msg = "Namespace packages cannot use editable mode 'wrapper'"
            raise ConfigError(msg)
        if self.module.get("generated") and any(
            e["mode"] == "wrapper" for e in self.editable.values()
        ):
            msg = "Generated modules/packages cannot use editable mode 'wrapper'"
            raise ConfigError(msg)


@dataclass
class ComponentConfig:
    """Describes the metadata and configuration settings for the component
    build backend."""

    standard_metadata: pyproject_metadata.StandardMetadata
    main_project: Path
    package_name: str = field(default="")
    component: dict[str, Any] = field(default_factory=dict)


@dataclass
class PackageInfo:
    """Describes a Python package (names and version)."""

    version: str
    package_name: str
    module_name: str

    @property
    def norm_name(self):
        from .util import normalize_name_wheel

        return normalize_name_wheel(self.package_name)


@dataclass
class BuildPaths:
    """Paths used when building a (Wheel) package."""

    source_dir: Path  # Contains pyproject.toml
    build_dir: Path  # Usually .py-build-cmake_cache, determined by config
    wheel_dir: Path  # Where to place the Wheel when done (given by frontend)
    temp_dir: Path  # Temporary folder for use during build
    staging_dir: Path  # Where to install the Python modules and data files
    pkg_staging_dir: Path  # The folder that will be turned into a Wheel

    # Note that staging_dir and pkg_staging_dir can be different, e.g. when
    # doing an editable install, all Python files and modules are installed to
    # staging_dir, which is a subfolder of build_dir, and pkg_staging_dir only
    # contains a .pth file that points to staging_dir


@dataclass
class Command:
    args: Sequence[str]
    kwargs: dict[str, Any]


def format_and_rethrow_exception(e: BaseException, component=False):
    """Raises a FormattedErrorMessage from the given exception"""
    if isinstance(e, FormattedErrorMessage):
        raise e
    if isinstance(e, ConfigError):
        logger.error("Error in user configuration", exc_info=False)
        comp_arg = " --component" if component else ""
        msg = (
            "\n"
            "\n"
            "\t\u274c Error in user configuration:\n"
            "\n"
            f"\t\t{e}\n"
            "\n"
            f"\t   Please run `py-build-cmake config format{comp_arg}` or see "
            "https://tttapa.github.io/py-build-cmake/reference/config.html for help.\n"
        )
        raise FormattedErrorMessage(msg) from e
    if isinstance(e, CalledProcessError):
        logger.error("Subprocess failed", exc_info=False)
        if e.cmd[:2] == ["cmake", "--build"]:
            msg = "CMake build failed"
        elif e.cmd[:2] == ["cmake", "--install"]:
            msg = "CMake install failed"
        elif e.cmd[:1] == ["cmake"]:
            msg = "CMake failed"
        elif e.cmd[:1] == ["stubgen"]:
            msg = "Stub generation failed"
        else:
            msg = f"Subprocess {e.cmd[0]} failed"
        msg = (
            f"\n\n\t\u274c {msg}:\n\n"
            f"\t\t{e}\n"
            "\n\t(scroll up for subprocess output, above Python backtrace)"
        )
        raise FormattedErrorMessage(msg) from e
    elif isinstance(e, AssertionError):
        logger.error("Internal error:", exc_info=e)
        msg = (
            "\n"
            "\n"
            "\t\u274c Internal error:\n"
            "\n"
            f"\t\t{e}\n"
            "\n"
            "\t   Please notify the developers: https://github.com/tttapa/py-build-cmake/issues\n"
        )
        raise FormattedErrorMessage(msg) from e
    elif isinstance(e, KeyError):
        logger.error("Internal KeyError:", exc_info=e)
        msg = (
            "\n"
            "\n"
            "\t\u274c Internal KeyError:\n"
            "\n"
            f"\t\t{e}\n"
            "\n"
            "\t   Please notify the developers: https://github.com/tttapa/py-build-cmake/issues\n"
        )
        raise FormattedErrorMessage(msg) from e
    elif isinstance(e, Exception):
        logger.error("Uncaught exception:", exc_info=e)
        msg = (
            "\n"
            "\n"
            f"\t\u274c Uncaught exception: {type(e).__name__}\n"
            "\n"
            f"\t\t{e}\n"
            "\n"
            "\t   Please notify the developers: https://github.com/tttapa/py-build-cmake/issues\n"
        )
        raise FormattedErrorMessage(msg) from e
