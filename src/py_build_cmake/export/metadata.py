from __future__ import annotations

import logging
import shutil
from copy import copy
from pathlib import Path

from ..common import Config

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


def write_entry_points(cfg: Config, distinfo_dir: Path):
    entrypoints = copy(cfg.standard_metadata.entrypoints)
    if cfg.standard_metadata.scripts:
        entrypoints["console_scripts"] = cfg.standard_metadata.scripts
    if cfg.standard_metadata.gui_scripts:
        entrypoints["gui_scripts"] = cfg.standard_metadata.gui_scripts
    with (distinfo_dir / "entry_points.txt").open("w", encoding="utf-8") as f:
        _write_entry_points(entrypoints, f)


def write_license_files(cfg: Config, distinfo_dir: Path):
    """Write the LICENSE file from pyproject.toml to the distinfo
    directory."""
    license = cfg.standard_metadata.license
    if not license:
        return
    if license.file:
        shutil.copy2(license.file, distinfo_dir)
    else:
        with (distinfo_dir / "LICENSE").open("w", encoding="utf-8") as f:
            f.write(license.text)


def write_metadata(cfg: Config, distinfo_dir: Path):
    metadata_path = distinfo_dir / "METADATA"
    with metadata_path.open("w", encoding="utf-8") as f:
        f.write(str(cfg.standard_metadata.as_rfc822()))
