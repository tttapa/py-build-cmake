from __future__ import annotations

import shutil
from pathlib import Path

from ..common import Module


def copy_pkg_source_to(staging_dir: Path, module: Module, symlink: bool = False):
    """Copy the files of a Python package to the build directory."""
    for src in module.iter_files_abs():
        rel_path = src.relative_to(module.prefix)
        dst = staging_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if symlink:
            dst.symlink_to(src, target_is_directory=False)
        else:
            shutil.copy2(src, dst, follow_symlinks=False)
