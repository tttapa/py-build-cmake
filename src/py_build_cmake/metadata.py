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

import ast
from contextlib import contextmanager
import logging
import sys
import distlib.version
from pathlib import Path
from typing import Optional, Dict, List

log = logging.getLogger(__name__)


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
    for child in node.body:
        # Only use the version from the given module if it's a simple
        # string assignment to __version__
        is_version_str = (
            isinstance(child, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__version__"
                for target in child.targets
            )
            and isinstance(child.value, ast.Str)
        )
        if is_version_str:
            version = child.value.s
            break
    else:
        version = None
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
    global _import_i
    _import_i += 1

    log.debug("Loading module %s", mod_filename)
    from importlib.util import spec_from_file_location, module_from_spec

    mod_name = "py_build_cmake.dummy.import%d" % _import_i
    spec = spec_from_file_location(mod_name, mod_filename)
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

    log.debug("Loading module %s", mod_filename)

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
            raise NoDocstringError(
                "The module '{}' is missing a docstring.".format(mod_filename)
            )
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
        raise NoVersionError(
            f"Please define a `__version__ = \"x.y.z\"` in your module '{filename}'."
        )
    if not isinstance(version, str):
        raise InvalidVersion(
            f"__version__ must be a string, not {type(version)}, in module '{filename}'."
        )

    try:
        norm_version = distlib.version.NormalizedVersion(version)
        version = str(norm_version)
    except distlib.version.UnsupportedVersionError as e:
        raise InvalidVersion(f"Invalid __version__ in module '{filename}': {str(e)}")

    return version


def write_entry_points(entrypoints: Dict[str, Dict[str, str]], fp):
    """Write entry_points.txt from a two-level dict

    Sorts on keys to ensure results are reproducible.
    """
    for group_name in sorted(entrypoints):
        fp.write("[{}]\n".format(group_name))
        group = entrypoints[group_name]
        for name in sorted(group):
            val = group[name]
            fp.write("{}={}\n".format(name, val))
        fp.write("\n")


# Own code
# --------------------------------------------------------------------------- #

from pyproject_metadata import StandardMetadata
from dataclasses import dataclass
import os


def update_dynamic_metadata(metadata: StandardMetadata, mod_filename: Optional[Path]):
    if mod_filename is None:
        if metadata.dynamic:
            raise ConfigError(
                "If no module is specified, dynamic metadata is not allowed"
            )
        return
    res = get_info_from_module(mod_filename, metadata.dynamic)
    if "version" in res:
        metadata.version = res["version"]
    if "summary" in res:
        metadata.description = res["summary"]


@dataclass
class Module:
    """
    TODO: distinction between paths relative to prefix and relative to base.
    """

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

        Yields absolute paths.
        Excludes any __pycache__ and *.pyc files.
        """

        def _include(p: Path):
            return not p.name == "__pycache__" and not p.name.endswith(".pyc")

        if self.is_package:
            # Ensure we sort all files and directories so the order is stable
            for dirpath, dirs, files in os.walk(str(self.full_path)):
                for file in sorted(files):
                    filepath = Path(dirpath) / file
                    if _include(filepath):
                        yield filepath
                dirs[:] = [d for d in sorted(dirs) if _include(Path(d))]
        else:
            yield self.full_file


def find_module(module_metadata: dict, src_dir: Path) -> Optional[Module]:
    name = module_metadata["name"]
    base_dir = src_dir / module_metadata["directory"]
    if name is None or base_dir is None:
        return None
    # Look for the module
    dir = lambda p: p.is_dir()
    file = lambda p: p.is_file()
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
        raise ConfigError(
            "Module is ambiguous {}: {}".format(
                name, ", ".join(map(str, sorted(found)))
            )
        )
    elif not found:
        raise ConfigError("No file/folder found for module {}".format(name))

    return Module(
        name=name,
        full_path=found[0][0],
        base_path=base_dir,
        is_package=found[0][1] == dir,
    )

def referenced_files(metadata: StandardMetadata) -> List[Path]:
    res = []
    if metadata.readme is not None and metadata.readme.file is not None:
        res += [metadata.readme.file]
    if metadata.license is not None and metadata.license.file is not None:
        res += [metadata.license.file]
    return res