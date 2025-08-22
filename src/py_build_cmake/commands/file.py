from __future__ import annotations

import typing

from .cmd_runner import CommandRunner


class VerboseFile:
    def __init__(self, runner: CommandRunner, path, descr: str):
        self.runner = runner
        self.path = path
        self.descr = descr
        self._file: typing.TextIO | None = None

    def __enter__(self):
        if self.runner.verbose:
            print(f"Writing {self.descr}\n{self.path}")
            print("---------------------------")
        if not self.runner.dry:
            self._file = open(self.path, "w", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file is not None and not self._file.closed:
            self._file.close()
        if self.runner.verbose:
            print("---------------------------\n", flush=True)

    def write(self, data):
        if self.runner.verbose:
            print(data, end="")
        if self._file is not None:
            return self._file.write(data)
        return 0

    def flush(self):
        if self._file is not None:
            return self._file.flush()
        return None

    def __getattr__(self, name):
        # Delegate everything else to the underlying file
        return getattr(self._file, name)
