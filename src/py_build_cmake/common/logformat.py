from __future__ import annotations

import logging
import os
from pathlib import Path


class GitHubActionsFormatter(logging.Formatter):
    """Formats warnings etc. for GitHub Actions: https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-notice-message"""

    def __init__(self):
        super().__init__(fmt="%(name)s:%(message)s")

    def format(self, record: logging.LogRecord):
        s = super().format(record)
        loc = ""
        if os.environ.get("GITHUB_REPOSITORY", "").endswith("/py-build-cmake"):
            p = Path(record.pathname)
            try:
                i = len(p.parts) - p.parts[-1::-1].index("py_build_cmake") - 1
                file = Path("src", *p.parts[i:])
                loc = f" file={file},line={record.lineno}"
            except ValueError:
                pass
        prefix = {
            logging.INFO: f"::notice{loc}::",
            logging.WARNING: f"::warning{loc}::",
            logging.ERROR: f"::error{loc}::",
        }.get(record.levelno, record.levelname + ":")
        return prefix + s
