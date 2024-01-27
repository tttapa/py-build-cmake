"""
The following functions are based on flit_core, under the BSD 3-Clause license:

Copyright (c) 2015, Thomas Kluyver and contributors
All rights reserved.

BSD 3-clause license:

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import annotations

import ast
import logging
import sys
from contextlib import contextmanager
from pathlib import Path

import distlib.version  # type: ignore[import-untyped]

from ..common import (
    ConfigError,
    InvalidVersion,
    Module,
    NoDocstringError,
    NoVersionError,
    ProblemInModule,
)

logger = logging.getLogger(__name__)


@contextmanager
def _module_load_ctx():
    """Preserve some global state that modules might change at import time.

    - Handlers on the root logger.
    """
    logging_handlers = logging.root.handlers[:]
    try:
        yield
    finally:
        logging.root.handlers = logging_handlers


def get_docstring_and_version_via_ast(mod_filename: Path):
    """
    Return a tuple like (docstring, version) for the given module,
    extracted by parsing its AST.
    """
    # read as bytes to enable custom encodings
    with mod_filename.open("rb") as f:
        node = ast.parse(f.read())
    version = None
    for child in node.body:
        # Only use the version from the given module if it's a simple
        # string assignment to __version__
        if (
            isinstance(child, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__version__"
                for target in child.targets
            )
            and isinstance(child.value, ast.Str)
        ):
            version = child.value.s
            break
    return ast.get_docstring(node), version


# To ensure we're actually loading the specified file, give it a unique name to
# avoid any cached import. In normal use we'll only load one module per process,
# so it should only matter for the tests, but we'll do it anyway.
_import_i = 0


def get_docstring_and_version_via_import(mod_filename: Path):
    """
    Return a tuple like (docstring, version) for the given module,
    extracted by importing the module and pulling __doc__ & __version__
    from it.
    """
    global _import_i  # noqa: PLW0603
    _import_i += 1

    logger.debug("Loading module %s", mod_filename)
    from importlib.util import module_from_spec, spec_from_file_location

    mod_name = "py_build_cmake.dummy.import%d" % _import_i
    spec = spec_from_file_location(mod_name, mod_filename)
    if spec is None:
        msg = f"Unable to import '{mod_filename}' (missing spec)"
        raise ProblemInModule(msg)
    if spec.loader is None:
        msg = f"Unable to import '{mod_filename}' (missing loader)"
        raise ProblemInModule(msg)
    with _module_load_ctx():
        m = module_from_spec(spec)
        # Add the module to sys.modules to allow relative imports to work.
        # importlib has more code around this to handle the case where two
        # threads are trying to load the same module at the same time, but Flit
        # should always be running a single thread, so we won't duplicate that.
        sys.modules[mod_name] = m
        try:
            spec.loader.exec_module(m)
        finally:
            sys.modules.pop(mod_name, None)

    docstring = m.__dict__.get("__doc__", None)
    version = m.__dict__.get("__version__", None)
    return docstring, version


def get_info_from_module(mod_filename: Path, for_fields=("version", "description")):
    """Load the module/package, get its docstring and __version__"""
    if not for_fields:
        return {}

    # What core metadata calls Summary, PEP 621 calls description
    want_summary = "description" in for_fields
    want_version = "version" in for_fields

    logger.debug("Loading module %s", mod_filename)

    # Attempt to extract our docstring & version by parsing our target's
    # AST, falling back to an import if that fails. This allows us to
    # build without necessarily requiring that our built package's
    # requirements are installed.
    docstring, version = get_docstring_and_version_via_ast(mod_filename)
    if (want_summary and not docstring) or (want_version and not version):
        docstring, version = get_docstring_and_version_via_import(mod_filename)

    res = {}

    if want_summary:
        if (not docstring) or not docstring.strip():
            msg = f"The module '{mod_filename}' is missing a docstring."
            raise NoDocstringError(msg)
        res["summary"] = docstring.lstrip().splitlines()[0]

    if want_version:
        res["version"] = check_version(version, mod_filename)

    return res


def check_version(version, filename):
    """
    Check whether a given version string match PEP 440, and do normalisation.

    Raise InvalidVersion/NoVersionError with relevant information if
    version is invalid.

    Log a warning if the version is not canonical with respect to PEP 440.

    Returns the version in canonical PEP 440 format.
    """
    if not version:
        msg = f"Please define a `__version__ = \"x.y.z\"` in your module '{filename}'."
        raise NoVersionError(msg)
    if not isinstance(version, str):
        msg = f"__version__ must be a string, not {type(version)}, in module '{filename}'."
        raise InvalidVersion(msg)

    try:
        norm_version = distlib.version.NormalizedVersion(version)
        version = str(norm_version)
    except distlib.version.UnsupportedVersionError as e:
        msg = f"Invalid __version__ in module '{filename}'"
        raise InvalidVersion(msg) from e

    return version


# Own code
# --------------------------------------------------------------------------- #

from pyproject_metadata import StandardMetadata  # noqa: E402


def update_dynamic_metadata(metadata: StandardMetadata, mod_filename: Path | None):
    if mod_filename is None:
        if metadata.dynamic:
            msg = "If no module is specified, dynamic metadata is not allowed"
            raise ConfigError(msg)
        return
    res = get_info_from_module(mod_filename, metadata.dynamic)
    if "version" in res:
        metadata.version = res["version"]
    if "summary" in res:
        metadata.description = res["summary"]
    metadata.dynamic = []


def find_module(module_metadata: dict, src_dir: Path) -> Module:
    name: str = module_metadata["name"]
    base_dir: Path = src_dir / module_metadata["directory"]
    is_namespace: bool = module_metadata["namespace"]
    generated: str | None = module_metadata.get("generated")

    # If the module is to be generated later by CMake, don't search for it now
    if generated:
        return Module(
            name=name,
            # This won't have the right extension, but that's not an issue
            full_path=base_dir / name,
            base_path=src_dir,
            is_package=generated == "package",
            is_namespace=is_namespace,
            is_generated=True,
        )

    # Look for the module
    dir = lambda p: p.is_dir()
    file = lambda p: not is_namespace and p.is_file()
    options = [
        (base_dir / name, dir),
        (base_dir / "src" / name, dir),
        (base_dir / (name + ".py"), file),
        (base_dir / "src" / (name + ".py"), file),
    ]

    def check(p: Path, checker):
        return checker(p)

    found = list(filter(lambda x: check(*x), options))

    if len(found) > 1:
        msg = f"Module is ambiguous {name}: {', '.join(map(repr, sorted(found)))}"
        raise ConfigError(msg)
    elif not found:
        msg = f"No file/folder found for module {name}"
        raise ConfigError(msg)

    full_path: Path = found[0][0]
    is_package = found[0][1] == dir

    if is_package:
        init_exists = (full_path / "__init__.py").exists()
        if is_namespace and init_exists:
            msg = (
                "Namespace packages should not contain __init__.py " f"(in {full_path})"
            )
            raise ConfigError(msg)
        elif not is_namespace and not init_exists:
            msg = (
                f"Missing __init__.py in {full_path}. "
                "Perhaps you forgot to set "
                "tool.py-build-cmake.module.namespace=true?"
            )
            raise ConfigError(msg)

    return Module(
        name=name,
        full_path=full_path,
        base_path=src_dir,
        is_package=is_package,
        is_namespace=is_namespace,
    )
