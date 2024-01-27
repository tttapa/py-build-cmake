from __future__ import annotations

import re
import sys
from pprint import pprint
from subprocess import CalledProcessError
from subprocess import run as sp_run

from distlib.version import NormalizedVersion  # type: ignore[import-untyped]


class CommandRunner:
    def __init__(self, verbose: bool = False, dry: bool = False):
        self.verbose = verbose
        self.dry = dry

    def run(self, *args, **kwargs):
        """Wrapper around subprocess.run that optionally prints the command."""
        if self.verbose:
            pprint([*args])
            pprint(kwargs)
            print(flush=True)
        elif self.dry:
            from shlex import join

            print(join(args[0]))
        if not self.dry:
            return sp_run(*args, **kwargs)  # noqa: PLW1510
        return None

    def check_program_version(
        self,
        program: str,
        minimum_version: NormalizedVersion | None,
        name: str | None,
        check_version: bool = True,
    ):
        """Check if there's a new enough version of the given command available
        in PATH."""
        name = name or program
        try:
            # Try running the command
            cmd = [program, "--version"] if check_version else [program, "-h"]
            res = self.run(cmd, check=True, capture_output=True, encoding="utf-8")
            # Try finding the version
            if res is not None and check_version:
                m = re.search(r"\d+(\.\d+){1,}", res.stdout)
                if not m:
                    msg = f"Unexpected {name} version output"
                    raise RuntimeError(msg)
                program_version = NormalizedVersion(m.group(0))
                if self.verbose:
                    print("Found", name, program_version)
                # Check if the version is new enough
                if minimum_version is not None and program_version < minimum_version:
                    msg = f"{name} too old"
                    raise RuntimeError(msg)
        except CalledProcessError as e:
            if self.verbose:
                print(f"{type(e).__module__}.{type(e).__name__}", e, sep=": ")
                print(e.stdout)
                print(e.stderr, file=sys.stderr)
            return False
        except Exception as e:
            # If any of that failed, return False
            if self.verbose:
                print(f"{type(e).__module__}.{type(e).__name__}", e, sep=": ")
            return False
        return True
