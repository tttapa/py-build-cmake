from __future__ import annotations

import html
import itertools
import os
import re
import shutil
import sys
import textwrap

from .config.options.config_option import ConfigOption, UncheckedConfigOption
from .config.options.default import RequiredValue
from .config.options.path import PathConfigOption


def _print_wrapped(text: str, indent, width: int | None = None):
    """Print the given string with the given indentation, wrapping it to the
    desired width, preserving line endings. If `width` is None, use the width
    of the terminal, or 80 columns as a fallback."""
    if width is None:
        width = shutil.get_terminal_size((80, 24)).columns
    text = text.replace("{docs_url}", "https://tttapa.github.io/py-build-cmake")
    text = text.replace("{docs_ext}", "html")
    wrapper = textwrap.TextWrapper(
        width=width, initial_indent=indent, subsequent_indent=indent
    )
    wrapped = [wrapper.wrap(i) for i in text.split("\n")]
    for line in itertools.chain.from_iterable(wrapped):
        print(line)


def get_default_str(opt: ConfigOption):
    """Get a string representation of the default value for the given option."""
    return opt.default.get_name()


def help_print_md(pbc_opts: ConfigOption):
    """
    Prints the top-level options in `pbc_opts` as MarkDown tables.
    """
    for k, v in pbc_opts.sub_options.items():
        if not v.sub_options:
            continue
        print("##", k)
        print(_get_full_description(v), "\n")
        print("| Option | Description | Type | Default |")
        print("|--------|-------------|------|---------|")
        for kk, vv in v.sub_options.items() or {}:
            typename = vv.get_typename(md=True) or ""
            print(
                "|",
                f'<a id="{k}.{kk}"></a>',
                f"`{kk}`",
                "|",
                _get_full_description(vv),
                "|",
                typename,
                "|",
                f"`{get_default_str(vv)}`",
                "|",
            )
        print()


def _get_full_description(vv: ConfigOption):
    descr = _md_escape(vv.description)
    if isinstance(vv, PathConfigOption):
        descr += "<br/>" + _describe_path_option(vv).capitalize() + "."
    if vv.inherits:
        descr += "<br/>Inherits from: `/" + str(vv.inherits) + "`"
    if vv.example:
        descr += "<br/>For example: `" + vv.example + "`"
    return descr


def _md_escape(descr: str):
    def unescape(m: re.Match):
        m0 = m.group(0)
        return html.unescape(m0.replace("\\*", "*"))

    descr = html.escape(descr).replace("*", "\\*")
    return (
        re.sub(r"`.*`", unescape, descr)
        .replace("\n", "<br/>")
        .replace("{docs_url}", "project:..")
        .replace("{docs_ext}", "md")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


def _should_use_colors():
    # Check the NO_COLOR environment variable
    if "NO_COLOR" in os.environ:
        return False
    # Check CLICOLOR and CLICOLOR_FORCE
    clicolor = os.environ.get("CLICOLOR", "1")
    clicolor_force = os.environ.get("CLICOLOR_FORCE", "0")
    if clicolor_force != "0":
        return True
    if clicolor == "0":
        return False
    # Check if output is a terminal
    if not sys.stdout.isatty():
        return False
    # Check the TERM environment variable
    term = os.environ.get("TERM", "")
    if term == "dumb":  # noqa: SIM103
        return False
    # Default to enabling colors
    return True


def _style(text: str, style: str):
    if _should_use_colors():
        return f"\x1b[{style}m{text}\x1b[0m"
    else:
        return text


def recursive_help_print(opt: ConfigOption, level=0):
    """Recursively prints the help messages for the options in `opt`."""
    for k, v in opt.sub_options.items():
        if isinstance(v, UncheckedConfigOption):
            continue
        indent = 4 * level * " "
        header = "\n" + _style(k, "1;4")
        if v.sub_options:
            header += ":"
            print(textwrap.indent(header, indent))
            if v.description:
                _print_wrapped(v.description, indent + "  ")
            recursive_help_print(v, level + 1)
        else:
            headerfields = []
            typename = v.get_typename()
            if typename is not None:
                headerfields += [_style(typename, "34")]
            if isinstance(v, PathConfigOption):
                headerfields += [_describe_path_option(v)]
            is_required = isinstance(v.default, RequiredValue)
            if is_required:
                headerfields += [_style("required", "31")]
            if v.inherits:
                headerfields += [_style("inherits from /" + str(v.inherits), "3")]
            if headerfields:
                header += " (" + ", ".join(headerfields) + ")"
            print(textwrap.indent(header + ":", indent))
            _print_wrapped(v.description, indent + "  ")
            if v.example:
                _print_wrapped("For example: " + v.example, indent + "  ")
            default = v.default.get_name()
            if not is_required:
                print(textwrap.indent("Default: " + default, indent + "  "))


def _describe_path_option(v: PathConfigOption):
    t = "absolute or relative" if v.allow_abs else "relative"
    if v.base_path is not None:
        t += " to " + v.base_path.description
    return t


def help_print(pbc_opts: ConfigOption):
    recursive_help_print(pbc_opts)
    print()
