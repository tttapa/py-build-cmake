"""
The following functions and classes are based on flit_core, under the BSD 3-Clause license:

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

from collections import defaultdict
from copy import copy
from glob import glob
from gzip import GzipFile
import io
import logging
import os
import os.path as osp
from pathlib import Path
from posixpath import join as pjoin
import tarfile

from ..common import Module, PackageInfo
from pyproject_metadata import StandardMetadata

logger = logging.getLogger(__name__)


def walk_data_dir(data_directory):
    """Iterate over the files in the given data directory.

    Yields paths prefixed with data_directory - caller may want to make them
    relative to that. Excludes any __pycache__ subdirectories.
    """
    if data_directory is None:
        return

    for dirpath, dirs, files in os.walk(data_directory):
        for file in sorted(files):
            full_path = os.path.join(dirpath, file)
            yield full_path

        dirs[:] = [d for d in sorted(dirs) if d != "__pycache__"]


def normalize_file_permissions(st_mode):
    """Normalize the permission bits in the st_mode field from stat to 644/755

    Popular VCSs only track whether a file is executable or not. The exact
    permissions can vary on systems with different umasks. Normalising
    to 644 (non executable) or 755 (executable) makes builds more reproducible.
    """
    # Set 644 permissions, leaving higher bits of st_mode unchanged
    new_mode = (st_mode | 0o644) & ~0o133
    if st_mode & 0o100:
        new_mode |= 0o111  # Executable: 644 -> 755
    return new_mode


def clean_tarinfo(ti, mtime=None):
    """Clean metadata from a TarInfo object to make it more reproducible.

    - Set uid & gid to 0
    - Set uname and gname to ""
    - Normalise permissions to 644 or 755
    - Set mtime if not None
    """
    ti = copy(ti)
    ti.uid = 0
    ti.gid = 0
    ti.uname = ""
    ti.gname = ""
    ti.mode = normalize_file_permissions(ti.mode)
    if mtime is not None:
        ti.mtime = mtime
    return ti


class FilePatterns:
    """Manage a set of file inclusion/exclusion patterns relative to basedir"""

    def __init__(self, patterns, basedir):
        self.basedir = basedir

        self.dirs = set()
        self.files = set()

        for pattern in patterns:
            for path in sorted(glob(osp.join(basedir, pattern), recursive=True)):
                rel = osp.relpath(path, basedir)
                if osp.isdir(path):
                    self.dirs.add(rel)
                else:
                    self.files.add(rel)

    def match_file(self, rel_path):
        if rel_path in self.files:
            return True

        return any(rel_path.startswith(d + os.sep) for d in self.dirs)

    def match_dir(self, rel_path):
        if rel_path in self.dirs:
            return True

        # Check if it's a subdirectory of any directory in the list
        return any(rel_path.startswith(d + os.sep) for d in self.dirs)


class SdistBuilder:
    """Builds a minimal sdist

    These minimal sdists should work for PEP 517.
    The class is extended in flit.sdist to make a more 'full fat' sdist,
    which is what should normally be published to PyPI.
    """

    def __init__(
        self,
        module: Module,
        pkg_info: PackageInfo,
        metadata: StandardMetadata,
        cfgdir,
        extra_files,
        include_patterns=(),
        exclude_patterns=(),
    ):
        self.module = module
        self.pkg_info = pkg_info
        self.metadata = metadata
        self.cfgdir = cfgdir
        self.extra_files = extra_files
        self.includes = FilePatterns(include_patterns, str(cfgdir))
        self.excludes = FilePatterns(exclude_patterns, str(cfgdir))

    def prep_entry_points(self):
        # Reformat entry points from dict-of-dicts to dict-of-lists
        res = defaultdict(list)
        for groupname, group in self.entrypoints.items():
            for name, ep in sorted(group.items()):
                res[groupname].append("{} = {}".format(name, ep))

        return dict(res)

    def select_files(self):
        """Pick which files from the source tree will be included in the sdist

        This is overridden in flit itself to use information from a VCS to
        include tests, docs, etc. for a 'gold standard' sdist.
        """
        make_rel = lambda p: p.relative_to(self.module.base_path)
        yield from map(make_rel, self.module.iter_files_abs())
        yield from map(make_rel, self.extra_files)

    def crucial_files(self):
        make_rel = lambda p: p.relative_to(self.module.base_path)
        yield make_rel(self.module.full_file)
        yield from map(make_rel, self.extra_files)

    def apply_includes_excludes(self, files):
        cfgdir_s = str(self.cfgdir)
        files = {f for f in files if not self.excludes.match_file(f)}

        for f_rel in self.includes.files:
            if not self.excludes.match_file(f_rel):
                files.add(Path(f_rel))

        for rel_d in self.includes.dirs:
            for dirpath, dirs, dfiles in os.walk(osp.join(cfgdir_s, rel_d)):
                for file in dfiles:
                    f_abs = osp.join(dirpath, file)
                    f_rel = osp.relpath(f_abs, cfgdir_s)
                    if not self.excludes.match_file(f_rel):
                        files.add(Path(f_rel))

                # Filter subdirectories before os.walk scans them
                dirs[:] = [
                    d
                    for d in dirs
                    if not self.excludes.match_dir(
                        osp.relpath(osp.join(dirpath, d), cfgdir_s)
                    )
                ]

        crucial_files = set(self.crucial_files())
        missing_crucial = crucial_files - files
        if missing_crucial:
            raise Exception(
                "Crucial files were excluded from the sdist: {}".format(
                    ", ".join(map(str, missing_crucial))
                )
            )

        return sorted(files)

    def add_setup_py(self, files_to_add, target_tarfile):
        """No-op here; overridden in flit to generate setup.py"""
        pass

    @property
    def dir_name(self):
        return f"{self.pkg_info.norm_name}-{self.pkg_info.version}"

    def build(self, target_dir, gen_setup_py=True):
        os.makedirs(str(target_dir), exist_ok=True)
        target = target_dir / (self.dir_name + ".tar.gz")
        source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH", "")
        mtime = int(source_date_epoch) if source_date_epoch else None
        gz = GzipFile(str(target), mode="wb", mtime=mtime)
        tf = tarfile.TarFile(
            str(target), mode="w", fileobj=gz, format=tarfile.PAX_FORMAT
        )

        try:
            files_to_add = self.apply_includes_excludes(self.select_files())

            for relpath in files_to_add:
                path = str(self.cfgdir / relpath)
                ti = tf.gettarinfo(path, arcname=pjoin(self.dir_name, relpath))
                ti = clean_tarinfo(ti, mtime)

                if ti.isreg():
                    with open(path, "rb") as f:
                        tf.addfile(ti, f)
                else:
                    tf.addfile(ti)  # Symlinks & ?

            if gen_setup_py:
                self.add_setup_py(files_to_add, tf)

            stream = io.StringIO()
            stream.write(str(self.metadata.as_rfc822()))
            pkg_info = stream.getvalue().encode()
            ti = tarfile.TarInfo(pjoin(self.dir_name, "PKG-INFO"))
            ti.size = len(pkg_info)
            tf.addfile(ti, io.BytesIO(pkg_info))

        finally:
            tf.close()
            gz.close()

        logger.debug("Built sdist: %s", target)
        return target
