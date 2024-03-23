from __future__ import annotations

from ...common import BuildPaths, Config, Module
from ...common.util import get_os_name
from .hook import write_editable_hook
from .symlink import write_editable_links
from .wrapper import write_editable_wrapper


def do_editable_install(cfg: Config, paths: BuildPaths, module: Module):
    edit_cfg = cfg.editable["cross" if cfg.cross else get_os_name()]
    mode = edit_cfg["mode"]
    if mode == "wrapper":
        write_editable_wrapper(paths.staging_dir, module)
    elif mode == "hook":
        write_editable_hook(paths.staging_dir, module)
    elif mode == "symlink":
        paths = write_editable_links(paths, module)
    else:
        msg = "Invalid editable mode"
        raise AssertionError(msg)
    return paths
