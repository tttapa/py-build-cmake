import html
import itertools
import shutil
import sys
import textwrap
from py_build_cmake.config import ConfigOption, ConfigOptionRef, get_config_options


def _print_wrapped(text, indent, width=None):
    """Print the given string with the given indentation, wrapping it to the
    desired width, preserving line endings. If `width` is None, use the width 
    of the terminal, or 80 columns as a fallback."""
    if width is None:
        width = shutil.get_terminal_size((80, 24)).columns
    wrapper = textwrap.TextWrapper(width=width,
                                   initial_indent=indent,
                                   subsequent_indent=indent)
    wrapped = [wrapper.wrap(i) for i in text.split('\n')]
    for line in itertools.chain.from_iterable(wrapped):
        print(line)


def get_default_str(opt: ConfigOption):
    """Get a string representation of the default value for the given option."""
    default = None
    if opt.default is ConfigOption.Required:
        default = 'required'
    if opt.default is ConfigOption.NoDefault:
        default = 'none'
    elif isinstance(opt.default, ConfigOptionRef):
        default = ConfigOption.stringify_prefix(opt.default.prefix)
    elif opt.default is not ConfigOption.Required:
        default = repr(opt.default)
    return default


def help_print_md(pbc_opts):
    """
    Prints the top-level options in `pbc_opts` as MarkDown tables.
    """
    for k, v in pbc_opts.items():
        print('##', k)
        print('| Option | Description | Type | Default |')
        print('|--------|-------------|------|---------|')
        for kk, vv in v.items():
            if not issubclass(type(vv), ConfigOption):
                continue
            print('|', f'`{kk}`', '|',
                  html.escape(vv.helpstring).replace('\n', '<br/>'), '|',
                  vv.get_typename(), '|', f'`{get_default_str(vv)}`', '|')


def recursive_help_print(opt, level=0):
    """Recursively prints the help messages for the options in `opt`."""
    for k, v in opt.items():
        if k == 'project':
            continue
        indent = 4 * level * ' '
        header = '\n' + k
        if isinstance(v, dict):
            header += ':'
            print(textwrap.indent(header, indent))
            recursive_help_print(v, level + 1)
        else:
            header += f' ({v.get_typename()}'
            if v.default is ConfigOption.Required:
                header += ', required'
            header += ')'
            print(textwrap.indent(header, indent))
            _print_wrapped(v.helpstring, indent + '  ')
            default = get_default_str(v)
            if default is not None:
                print(textwrap.indent('Default: ' + default, indent + '  '))

def _print_usage():
    print(textwrap.dedent("""\
    Print the documentation for the pyproject.toml configuration options for the
    py-build-cmake build backend.

    Usage:
    """))
    name = __loader__.name.rsplit(sep='.', maxsplit=1)[0]
    print("   ", sys.executable, "-m", name, "[md]")
    print(textwrap.dedent("""
    Use the 'md' option to print the options as a MarkDown table instead of a
    plain-text list.
    """))

if __name__ == '__main__':
    opts = get_config_options('tool.py-build-cmake')
    help_opt = {'-h', '-?', '--help', 'h', 'help', '?'}
    if len(sys.argv) > 1 and sys.argv[1] == 'md':
        pbc_opts = opts.get_option('tool.py-build-cmake')
        help_print_md(pbc_opts)
    elif len(sys.argv) > 1 or set(map(str.lower, sys.argv[1:])) & help_opt:
        _print_usage()
    else:
        print("List of py-build-cmake pyproject.toml options.")
        recursive_help_print(opts.options)
        print()
