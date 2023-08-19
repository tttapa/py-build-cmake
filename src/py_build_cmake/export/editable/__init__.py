from ...common import BuildPaths, Module
from ...common.util import get_os_name
from .wrapper import write_editable_wrapper
from .hook import write_editable_hook
from .symlink import write_editable_links

def do_editable_install(cfg, paths: BuildPaths, module: Module):
    edit_cfg = cfg.editable['cross' if cfg.cross else get_os_name()]
    mode = edit_cfg["mode"]
    if mode == "wrapper":
        write_editable_wrapper(paths.staging_dir, module)
    elif mode == "hook":
        write_editable_hook(paths.staging_dir, module),
    elif mode == "symlink":
        paths = write_editable_links(paths, module)
    else:
        assert False, "Invalid editable mode"
    return paths
