from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

from ...common import ConfigError, Module


def write_editable_wrapper(staging_dir: Path, module: Module):
    """Write a fake __init__.py file that points to the development folder."""
    if not module.is_package:
        msg = "Editable wrapper mode is not supported for stand-alone Python modules."
        raise ConfigError(msg)
    name = module.name
    tmp_pkg = staging_dir / name
    pkgpath = module.full_path
    initpath = pkgpath / "__init__.py"
    tmp_pkg.mkdir(parents=True, exist_ok=True)
    special_dunders = [
        "__builtins__",
        "__cached__",
        "__file__",
        "__loader__",
        "__name__",
        "__package__",
        "__path__",
        "__spec__",
    ]
    content = f"""\
        # First extend the search path with the development folder
        __spec__.submodule_search_locations.insert(0, {str(pkgpath)!a})
        # Now manually import the development __init__.py
        from importlib import util as _util
        _spec = _util.spec_from_file_location("{name}",
                                                {str(initpath)!a})
        _mod = _util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        # After importing, add its symbols to our global scope
        _vars = _mod.__dict__.copy()
        for _k in ['{"','".join(special_dunders)}']: _vars.pop(_k)
        globals().update(_vars)
        # Clean up
        del _k, _spec, _mod, _vars, _util
        """
    (tmp_pkg / "__init__.py").write_text(textwrap.dedent(content), encoding="utf-8")
    # Add the py.typed file if it exists, so mypy picks up the stubs for
    # the C++ extensions
    py_typed = module.full_path / "py.typed"
    if py_typed.exists():
        shutil.copy2(py_typed, tmp_pkg)
    # Write a path file so IDEs find the correct files as well
    (staging_dir / f"{name}.pth").write_text(f"{module.full_path.parent!s}\n")
