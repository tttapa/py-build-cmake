from __future__ import annotations

import logging
import os
import time
import zipfile
from pathlib import Path

from distlib.wheel import Wheel  # type: ignore[import-untyped]

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
