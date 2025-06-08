from __future__ import annotations

import logging
import shutil
from copy import copy
from pathlib import Path

import pyproject_metadata

from ..common import ComponentConfig, Config

logger = logging.getLogger(__name__)


def _write_entry_points(entrypoints: dict[str, dict[str, str]], fp):
    """Write entry_points.txt from a two-level dict

    Sorts on keys to ensure results are reproducible.

    Based on flit_core.
    """
    for group_name in sorted(entrypoints):
        fp.write(f"[{group_name}]\n")
        group = entrypoints[group_name]
        for name in sorted(group):
            val = group[name]
            fp.write(f"{name}={val}\n")
        fp.write("\n")


def write_entry_points(cfg: Config | ComponentConfig, distinfo_dir: Path):
    entrypoints = copy(cfg.standard_metadata.entrypoints)
    if cfg.standard_metadata.scripts:
        entrypoints["console_scripts"] = cfg.standard_metadata.scripts
    if cfg.standard_metadata.gui_scripts:
        entrypoints["gui_scripts"] = cfg.standard_metadata.gui_scripts
    with (distinfo_dir / "entry_points.txt").open("w", encoding="utf-8") as f:
        _write_entry_points(entrypoints, f)


def write_license_files(
    cfg: Config | ComponentConfig, src_dir: Path, distinfo_dir: Path
):
    """Write the LICENSE file from pyproject.toml to the distinfo
    directory, and copy license-files."""
    license = cfg.standard_metadata.license
    license_files = cfg.standard_metadata.license_files
    # From https://packaging.python.org/en/latest/specifications/pyproject-toml/#license-files
    # If the license-files key is present and is set to a value of an empty
    # array, then tools MUST NOT include any license files and MUST NOT raise
    # an error.
    if license_files is not None and not license_files:
        return
    if isinstance(license, pyproject_metadata.License):
        if license.file:
            shutil.copy2(src_dir / license.file, distinfo_dir)
        else:
            with (distinfo_dir / "LICENSE").open("w", encoding="utf-8") as f:
                f.write(license.text)
    # https://peps.python.org/pep-0639
    if license_files:
        for p in license_files:
            dst = distinfo_dir / "licenses" / p
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_dir / p, dst)


def write_metadata(cfg: Config | ComponentConfig, distinfo_dir: Path):
    metadata_path = distinfo_dir / "METADATA"
    with metadata_path.open("w", encoding="utf-8") as f:
        f.write(str(cfg.standard_metadata.as_rfc822()))
