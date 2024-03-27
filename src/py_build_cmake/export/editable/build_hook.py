from __future__ import annotations

import logging
import textwrap
from pathlib import Path

from ...commands.cmake import CMaker
from ...common import Config, Module
from ...common.util import get_os_name

logger = logging.getLogger(__name__)


def write_build_hook(cfg: Config, staging_dir: Path, module: Module, cmaker: CMaker):
    """Write a hook that re-compiles extension modules."""
    edit_cfg = cfg.editable["cross" if cfg.cross else get_os_name()]
    if not edit_cfg.get("build_hook"):
        return
    if edit_cfg.get("mode") != "symlink":
        logger.warning("Skipping build_hook: only supported for symlink mode")
        return
    name = module.name
    pkg_hook = staging_dir / (name + "_build_hook")
    pkg_hook.mkdir(parents=True, exist_ok=True)
    cwd = cmaker.get_working_dir()
    env = cmaker.conf_settings.environment or {}
    cmd = list(cmaker.get_build_commands()) + list(cmaker.get_install_commands())
    content = f"""\
        import sys, inspect, os
        from importlib.machinery import PathFinder
        from string import Template
        import subprocess

        class BuilderPathFinder(PathFinder):
            def __init__(self, name, cwd, env, cmd):
                self.name = name
                self.cwd = cwd
                self.env = env
                self.cmd = cmd
            def find_spec(self, name, path=None, target=None):
                if name.split('.', 1)[0] == self.name:
                    self.build()
                return None
            def prepare_environment(self):
                env = os.environ.copy()
                for k, v in self.env.items():
                    templ = Template(v)
                    env[k] = templ.substitute(env)
                return env
            def build(self):
                env = self.prepare_environment()
                for cmd in self.cmd:
                    try:
                        subprocess.run(cmd, cwd=self.cwd, check=True, env=env)
                    except subprocess.CalledProcessError as e:
                        raise ImportError(
                            f"Failed to build dependencies for module {{self.name!r}}",
                            name=self.name,
                            path=self.cwd,
                        ) from e
                sys.meta_path.remove(self)

        def install(name: str, cwd, env, cmd):
            sys.meta_path.insert(0, BuilderPathFinder(name, cwd, env, cmd))

        install(
            name={name!r},
            cwd={cwd!r},
            env={env!r},
            cmd={cmd!r},
        )
        """
    (pkg_hook / "__init__.py").write_text(textwrap.dedent(content), encoding="utf-8")
    # Write a path file to find the development files
    content = f"import {name}_build_hook\n"
    with (staging_dir / f"{name}.pth").open("a") as f:
        f.write(content)
