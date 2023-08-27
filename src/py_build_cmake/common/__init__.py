from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import pyproject_metadata

logger = logging.getLogger(__name__)


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

    @property
    def prefix(self):
        return self.full_path.parent

    @property
    def full_file(self):
        if self.is_package:
            return self.full_path / "__init__.py"
        else:
            return self.full_path

    def iter_files_abs(self):
        """Iterate over the files contained in this module.
        Yields absolute paths. Excludes any __pycache__ and *.pyc files.
        """

        def _include(p):
            p = Path(p)
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
    module: dict[str, str] = field(default_factory=dict)
    editable: dict[str, Any] = field(default_factory=dict)
    sdist: dict[str, dict[str, Any]] = field(default_factory=dict)
    cmake: dict[str, Any] | None = field(default=None)
    stubgen: dict[str, Any] | None = field(default=None)
    cross: dict[str, Any] | None = field(default=None)

    @property
    def referenced_files(self) -> list[Path]:
        metadata = self.standard_metadata
        res = []
        if metadata.readme is not None and metadata.readme.file is not None:
            res += [metadata.readme.file]
        if metadata.license is not None and metadata.license.file is not None:
            res += [metadata.license.file]
        return res


@dataclass
class ComponentConfig:
    """Describes the metadata and configuration settings for the component
    build backend."""

    standard_metadata: pyproject_metadata.StandardMetadata
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
