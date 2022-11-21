import sys
import textwrap
from pathlib import Path

from ..pyproject_options import get_options
from ..config_options import pth
from . import help_print_md, help_print


def _print_usage():
    print(
        textwrap.dedent("""\
    Print the documentation for the pyproject.toml configuration options for the
    py-build-cmake build backend.

    Usage:
    """))
    name = __loader__.name.rsplit(sep='.', maxsplit=1)[0]
    print("   ", sys.executable, "-m", name, "[md]")
    print(
        textwrap.dedent("""
    Use the 'md' option to print the options as a MarkDown table instead of a
    plain-text list.
    """))


def main():
    opts = get_options(Path('/'))
    help_pth = pth('pyproject.toml/tool/py-build-cmake')
    pbc_opts = opts[help_pth]
    help_opt = {'-h', '-?', '--help', 'h', 'help', '?'}
    if len(sys.argv) == 2 and sys.argv[1] == 'md':
        help_print_md(pbc_opts)
    elif len(sys.argv) > 1 or set(map(str.lower, sys.argv[1:])) & help_opt:
        _print_usage()
    else:
        help_print(pbc_opts)


if __name__ == '__main__':
    main()