# ruff: noqa: PLR0912, PLR0915, RUF015, UP031, PTH112, B007, PTH118, PTH123, PLW2901
# This code was largely copied from distlib to work around
# https://github.com/pypa/distlib/issues/246, and it does not comply with the
# ruff warnings used throughout py-build-cmake, so we ignore the entire file for
# now.

from __future__ import annotations

import logging
import os
import time
import zipfile
from pathlib import Path

import distlib  # type: ignore[import-untyped]
from distlib.wheel import (  # type: ignore[import-untyped]
    ABI,
    ARCH,
    IMPVER,
    PYVER,
    Wheel,
    fsdecode,
    to_posix,
)

logger = logging.getLogger(__name__)


class WheelBuilder(Wheel):
    def _get_source_time(self):
        """
        Get the value of the SOURCE_DATE_EPOCH in a format to pass to ZipInfo.
        https://reproducible-builds.org/docs/source-date-epoch/
        """
        if "SOURCE_DATE_EPOCH" not in os.environ:
            return None
        source_date_epoch = os.environ["SOURCE_DATE_EPOCH"]
        try:
            filetime = int(source_date_epoch)
        except ValueError:
            msg = "SOURCE_DATE_EPOCH is not an integer, so I'm ignoring it."
            logger.warning(msg)
            return None
        return time.gmtime(max(315532800, filetime))

    def build_zip(self, pathname: str | Path, archive_paths: list[tuple[str, str]]):
        """
        We override this method to ensure a consistent modification time for all
        files in the ZIP if the SOURCE_DATE_EPOCH environment variable is set.
        """
        filetime = self._get_source_time()
        if filetime is None:
            super().build_zip(pathname, archive_paths)
            return
        tmstr = time.strftime("%Y-%m-%dT%H:%M:%S", filetime)
        msg = f"SOURCE_DATE_EPOCH is set, using mtime={tmstr} for files in Wheel"
        logger.info(msg)
        with zipfile.ZipFile(pathname, "w", zipfile.ZIP_DEFLATED) as zf:
            for ap, p in archive_paths:
                file_zipinfo = zipfile.ZipInfo(ap, date_time=filetime)
                zf.writestr(file_zipinfo, Path(p).read_bytes())
                logger.debug("Wrote %s to %s in wheel", p, ap)

    # fmt: off
    def build(self, paths, tags=None, wheel_version=None):
        """
        Build a wheel from files in specified paths, and use any specified tags
        when determining the name of the wheel.

        This function patches the distlib.wheel.Wheel.build function, awaiting
        the release of https://github.com/pypa/distlib/pull/247

        TODO: remove this override once released, and update the distlib version
              requirements in pyproject.toml and .pre-commit-config.yaml.
              Then also remove the ruff: noqa from this file.
        """
        if tags is None:
            tags = {}

        libkey = list(filter(lambda o: o in paths, ('purelib', 'platlib')))[0]
        if libkey == 'platlib':
            is_pure = 'false'
            default_pyver = [IMPVER]
            default_abi = [ABI]
            default_arch = [ARCH]
        else:
            is_pure = 'true'
            default_pyver = [PYVER]
            default_abi = ['none']
            default_arch = ['any']

        self.pyver = tags.get('pyver', default_pyver)
        self.abi = tags.get('abi', default_abi)
        self.arch = tags.get('arch', default_arch)

        libdir = paths[libkey]

        name_ver = '%s-%s' % (self.name, self.version)
        data_dir = '%s.data' % name_ver
        info_dir = '%s.dist-info' % name_ver

        archive_paths = []

        # First, stuff which is not in site-packages
        for key in ('data', 'headers', 'scripts'):
            if key not in paths:
                continue
            path = paths[key]
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for fn in files:
                        p = fsdecode(os.path.join(root, fn))
                        rp = os.path.relpath(p, path)
                        ap = to_posix(os.path.join(data_dir, key, rp))
                        archive_paths.append((ap, p))
                        if key == 'scripts' and not p.endswith('.exe'):
                            with open(p, 'rb') as f:
                                data = f.read()
                            data = self.process_shebang(data)
                            with open(p, 'wb') as f:
                                f.write(data)

        # Now, stuff which is in site-packages, other than the
        # distinfo stuff.
        path = libdir
        distinfo = None
        for root, dirs, files in os.walk(path):
            if root == path:
                # At the top level only, save distinfo for later
                # and skip it for now
                for i, dn in enumerate(dirs):
                    dn = fsdecode(dn)
                    if dn.endswith('.dist-info'):
                        distinfo = os.path.join(root, dn)
                        del dirs[i]
                        break
                assert distinfo, '.dist-info directory expected, not found'

            for fn in files:
                # comment out next suite to leave .pyc files in
                if fsdecode(fn).endswith(('.pyc', '.pyo')):
                    continue
                p = os.path.join(root, fn)
                rp = to_posix(os.path.relpath(p, path))
                archive_paths.append((rp, p))

        # Now distinfo. It may contain subdirectories (e.g. PEP 639)
        for root, _, files in os.walk(distinfo):
            for fn in files:
                if fn not in ('RECORD', 'INSTALLER', 'SHARED', 'WHEEL'):
                    p = fsdecode(os.path.join(root, fn))
                    r = os.path.relpath(root, distinfo)
                    ap = to_posix(os.path.normpath(os.path.join(info_dir, r, fn)))
                    archive_paths.append((ap, p))

        wheel_metadata = [
            'Wheel-Version: %d.%d' % (wheel_version or self.wheel_version),
            'Generator: distlib %s' % distlib.__version__,
            'Root-Is-Purelib: %s' % is_pure,
        ]
        if self.buildver:
            wheel_metadata.append('Build: %s' % self.buildver)
        for pyver, abi, arch in self.tags:
            wheel_metadata.append('Tag: %s-%s-%s' % (pyver, abi, arch))
        p = os.path.join(distinfo, 'WHEEL')
        with open(p, 'w') as f:
            f.write('\n'.join(wheel_metadata))
        ap = to_posix(os.path.join(info_dir, 'WHEEL'))
        archive_paths.append((ap, p))

        # sort the entries by archive path. Not needed by any spec, but it
        # keeps the archive listing and RECORD tidier than they would otherwise
        # be. Use the number of path segments to keep directory entries together,
        # and keep the dist-info stuff at the end.
        def sorter(t):
            ap = t[0]
            n = ap.count('/')
            if '.dist-info' in ap:
                n += 10000
            return (n, ap)

        archive_paths = sorted(archive_paths, key=sorter)

        # Now, at last, RECORD.
        # Paths in here are archive paths - nothing else makes sense.
        self.write_records((distinfo, info_dir), libdir, archive_paths)
        # Now, ready to build the zip file
        pathname = os.path.join(self.dirname, self.filename)
        self.build_zip(pathname, archive_paths)
        return pathname
    # fmt: on
