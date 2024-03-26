from __future__ import annotations

import textwrap
from pathlib import Path

from ...common import Module


def write_editable_hook(staging_dir: Path, module: Module):
    """Write a hook that finds the installed compiled extension modules."""
    name = module.name
    pkg_hook = staging_dir / (name + "_editable_hook")
    pkg_hook.mkdir(parents=True, exist_ok=True)
    content = f"""\
        import sys, inspect, os
        from importlib.machinery import PathFinder

        class EditablePathFinder(PathFinder):
            def __init__(self, name, extra_path):
                self.name = name
                self.extra_path = extra_path
            def find_spec(self, name, path=None, target=None):
                if name.split('.', 1)[0] != self.name:
                    return None
                if path is None:
                    path = []
                path.append(self.extra_path)
                return super().find_spec(name, path, target)

        def install(name: str):
            source_path = os.path.abspath(inspect.getsourcefile(EditablePathFinder))
            source_dir = os.path.dirname(source_path)
            installed_path = os.path.join(source_dir, '..', name)
            sys.meta_path.insert(0, EditablePathFinder(name, installed_path))

        install('{name}')
        """
    (pkg_hook / "__init__.py").write_text(textwrap.dedent(content), encoding="utf-8")
    # Write a path file to find the development files
    content = f"{module.full_path.parent!s}\n" f"import {name}_editable_hook\n"
    (staging_dir / f"{name}.pth").write_text(textwrap.dedent(content))
