import os
import sys
from contextlib import AbstractContextManager

if sys.version_info < (3, 11):

    # https://github.com/python/cpython/blob/6fcac09401e336b25833dcef2610d498e73b27a1/Lib/contextlib.py#L802
    class chdir(AbstractContextManager):
        """Non thread-safe context manager to change the current working directory."""

        def __init__(self, path):
            self.path = path
            self._old_cwd = []

        def __enter__(self):
            self._old_cwd.append(os.getcwd())  # noqa: PTH109
            os.chdir(self.path)

        def __exit__(self, *excinfo):
            os.chdir(self._old_cwd.pop())

else:
    from contextlib import chdir

__all__ = ["chdir"]
