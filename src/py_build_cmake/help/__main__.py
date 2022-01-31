import itertools
import shutil
import textwrap
from py_build_cmake.config import ConfigOption, ConfigOptionRef, get_config_options


def _print_wrapped(text, indent, width=None):
    if width is None:
        width = shutil.get_terminal_size((80, 24)).columns
    wrapper = textwrap.TextWrapper(width=width,
                                   initial_indent=indent,
                                   subsequent_indent=indent)
    wrapped = [wrapper.wrap(i) for i in text.split('\n')]
    for line in itertools.chain.from_iterable(wrapped):
        print(line)


if __name__ == '__main__':
    opts = get_config_options('tool.py-build-cmake')

    def rec_help_print(opt, level=0):
        for k, v in opt.items():
            if k == 'project':
                continue
            indent = 4 * level * ' '
            header = '\n' + k
            if isinstance(v, dict):
                header += ':'
                print(textwrap.indent(header, indent))
                rec_help_print(v, level + 1)
            else:
                header += f' ({v.get_typename()}'
                if v.default is ConfigOption.Required:
                    header += ', required'
                header += ')'
                print(textwrap.indent(header, indent))
                _print_wrapped(v.helpstring, indent + '  ')
                default = None
                if v.default is ConfigOption.NoDefault:
                    default = 'none'
                elif isinstance(v.default, ConfigOptionRef):
                    default = ConfigOption.stringify_prefix(v.default.prefix)
                elif v.default is not ConfigOption.Required:
                    default = repr(v.default)
                if default is not None:
                    print(textwrap.indent('Default: ' + default,
                                          indent + '  '))

    print("List of py-build-cmake pyproject.toml options.")
    rec_help_print(opts.options)
    print()
