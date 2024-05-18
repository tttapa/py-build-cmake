from __future__ import annotations

from pathlib import Path

import click

from . import __version__


def cmake_command(directory, build_path, verbose, dry, native, cross, local):
    def get_cmaker():
        from .build import _BuildBackend as backend
        from .commands.cmd_runner import CommandRunner

        src_dir = Path(directory or ".").resolve()
        config_settings = {
            "--cross": list(cross),
            "--local": list(local),
        }
        # Read configuration and package metadata
        cfg, module = backend.read_all_metadata(src_dir, config_settings, verbose)
        pkg_info = backend.get_pkg_info(cfg, module)
        cmake_cfg = backend.get_cmake_config(cfg)

        # Set up all paths
        build_cfg_name = backend.get_build_config_name(cfg.cross)
        build_dir = Path(cmake_cfg["build_path"]) / build_cfg_name

        # CMake builder
        return backend.get_cmaker(
            src_dir,
            build_dir,
            None,
            cmake_cfg,
            cfg.cross,
            pkg_info,
            runner=CommandRunner(verbose=verbose, dry=dry),
        )

    return get_cmaker


@click.group()
@click.option(
    "-C",
    "--directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=False,
    help="The directory containing pyproject.toml.",
)
@click.option(
    "-B",
    "--build-path",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    required=False,
    default=None,
    help="Override py-build-cmake's default build folder.",
)
@click.option(
    "-V",
    "--verbose",
    is_flag=True,
    help="Print verbose information about the commands being executed.",
)
@click.option(
    "-n",
    "--dry",
    is_flag=True,
    help="Print the commands without actually invoking CMake.",
)
@click.option(
    "--native",
    is_flag=True,
    help="When the configuration requests cross-compiling, "
    "configure for a native build instead. Has no effect otherwise.",
)
@click.option(
    "--local",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
    required=False,
    multiple=True,
    help="Specifies a toml file that overrides the "
    "tool.py-build-cmake section of pyproject.toml, "
    "similar to py-build-cmake.local.toml.",
)
@click.option(
    "--cross",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
    required=False,
    multiple=True,
    help="Specifies a toml file that overrides the "
    "tool.py-build-cmake.cross section of pyproject.toml, "
    "similar to py-build-cmake.cross.toml.",
)
@click.version_option(__version__, "-v", "--version", prog_name="py-build-cmake")
@click.pass_context
def cli(ctx: click.Context, **kwargs):
    ctx.obj = cmake_command(**kwargs)


@cli.command(help="Configure the CMake project.")
@click.pass_obj
@click.option(
    "--preset",
    nargs=1,
    type=str,
    required=False,
    metavar="PRESET",
    help="CMake configure preset to use.",
)
@click.option(
    "--use-build-presets",
    is_flag=True,
    help="Indicate that a build preset will be used during the build stage. "
    "This causes py-build-cmake to let CMake pick the build directory during "
    "configuration, rather than explicitly overriding it.",
)
@click.argument("args", nargs=-1, required=False)
def configure(obj, preset, use_build_presets, args):
    cmaker = obj()
    if cmaker is None:
        return
    cmaker.conf_settings.args += args or []
    if preset is not None:
        cmaker.conf_settings.preset = preset
    if use_build_presets:
        cmaker.build_settings.presets = [""]
    cmaker.configure()


@cli.command(help="Build the CMake project.")
@click.pass_obj
@click.option(
    "--preset", nargs=1, multiple=True, type=str, required=False, metavar="PRESET"
)
@click.option(
    "--config", nargs=1, multiple=True, type=str, required=False, metavar="CONFIG"
)
@click.argument("args", nargs=-1, required=False)
def build(obj, preset, config, args):
    cmaker = obj()
    if cmaker is None:
        return
    cmaker.build_settings.args += args or []
    if preset or config:
        cmaker.build_settings.presets = []
        cmaker.build_settings.configs = []
    if preset:
        cmaker.build_settings.presets = preset
    if config:
        cmaker.build_settings.configs = config
    cmaker.build()


@cli.command(help="Install the CMake project.")
@click.pass_obj
@click.option(
    "--config", nargs=1, multiple=True, type=str, required=False, metavar="CONFIG"
)
@click.option(
    "--component", nargs=1, multiple=True, type=str, required=False, metavar="COMP"
)
@click.argument("args", nargs=-1, required=False)
def install(obj, config, component, args):
    cmaker = obj()
    if cmaker is None:
        return
    cmaker.install_settings.args += args or []
    if config:
        cmaker.install_settings.configs = config
    if component:
        cmaker.install_settings.components = component
    cmaker.install()


@cli.group(help="Config file operations.")
def config():
    pass


@config.command(help="Print documentation for the config file format.")
@click.option("--md", is_flag=True, help="Use the MarkDown format.")
@click.option(
    "--component", is_flag=True, help="Documentation for the build_component backend."
)
def format(md, component):
    from .config.options.config_path import ConfPath
    from .config.options.config_reference import ConfigReference
    from .config.options.pyproject_options import get_component_options, get_options

    if md:
        from .help import help_print_md as help_print
    else:
        from .help import help_print
    help_pth = ConfPath.from_string("pyproject.toml/tool/py-build-cmake")
    pr_md = print if md else lambda *args, **kwargs: None
    pr_tx = lambda *args, **kwargs: None if md else print
    if component:
        pr_tx(
            "List of py-build-cmake pyproject.toml options for the "
            "build_component backend:"
        )
        pr_md(
            "# py-build-cmake component build backend\n"
            "The `py_build_cmake.build_component` build backend allows "
            "building packages containing additional binaries that are not "
            "included with the main distribution.\n"
        )
        pr_md(
            "A possible use case is distributing debug symbols: these files "
            "can be large, and most users don't need them, so distributing "
            "them in a separate package makes sense.\n"
        )
        pr_md(
            "See [examples/minimal-debug-component](https://github.com/tttapa/"
            "py-build-cmake/tree/main/examples/minimal-debug-component) "
            "for more information.\n"
        )
        opts = get_component_options(Path("/"))
        root_ref = ConfigReference(ConfPath.from_string("/"), opts)
        help_print(root_ref.sub_ref(help_pth).config)

    else:
        pr_tx("List of py-build-cmake pyproject.toml options:")
        pr_md("# py-build-cmake configuration options\n")
        pr_md(
            "These options go in the `[tool.py-build-cmake]` section of "
            "the `pyproject.toml` configuration file.\n"
        )
        opts = get_options(Path("/"))
        root_ref = ConfigReference(ConfPath.from_string("/"), opts)
        help_print(root_ref.sub_ref(help_pth).config)
        pr_md("# Local overrides\n")
        pr_md(
            "Additionally, two extra configuration files can be placed in "
            "the same directory as `pyproject.toml` to override some "
            "options for your specific use case:\n\n"
            "- `py-build-cmake.local.toml`: the options in this file "
            "override the values in the `tool.py-build-cmake` section of "
            "`pyproject.toml`.<br/>This is useful if you need specific "
            "arguments or CMake options to compile the package on your "
            "system.\n"
            "- `py-build-cmake.cross.toml`: the options in this file "
            "override the values in the `tool.py-build-cmake.cross` section "
            "of `pyproject.toml`.<br/>Useful for cross-compiling the "
            "package without having to edit the main configuration file.\n"
        )
        pr_md("# Command line overrides\n")
        pr_md(
            "Instead of using the `py-build-cmake.local.toml` and "
            "`py-build-cmake.cross.toml` files, you can also include "
            "additional config files using command line options:\n\n"
            "- `--local`: specifies a toml file that overrides the "
            "`tool.py-build-cmake` section of `pyproject.toml`, "
            "similar to `py-build-cmake.local.toml`\n"
            "- `--cross`: specifies a toml file that overrides the "
            "`tool.py-build-cmake.cross` section of `pyproject.toml`, "
            "similar to `py-build-cmake.cross.toml`\n\n"
            "These command line overrides are applied after the "
            "`py-build-cmake.local.toml` and `py-build-cmake.cross.toml` "
            "files in the project folder (if any).\n\n"
            "When using PyPA build, these flags can be specified using "
            "the `-C` or `--config-setting` flag: \n"
            "```sh\n"
            "python -m build . -C--cross=/path/to/my-cross-config.toml\n"
            "```\n"
            "The same flag may appear multiple times, for example: \n"
            "```sh\n"
            "python -m build . -C--local=conf-A.toml -C--local=conf-B.toml\n"
            "```\n"
            "For PyPA pip, you can use the `--config-settings` flag "
            "instead.\n"
        )
        pr_md("# Combining lists\n")
        pr_md(
            "Many options are specified as lists of strings. When one of "
            "these options inherits from or is overridden by another option, "
            "these lists can be merged in different ways.\n\n"
            "In the table above, when the data type is `list`, the original "
            "list of options is simply replaced by the list it is overridden "
            "by.  \n"
            "When the data type is `list+`, the value of the overriding "
            "option is appended to the original value. This is used primarily "
            "for combining lists of command line options.\n\n"
            "If you want full control of what happens when overriding a list "
            "option, you can use a dictionary with one or more of the "
            "following keys:\n\n"
            '  - `"="`: replace the original list by this list (default '
            "behavior for options of type `list`)\n"
            '  - `"+"`: append the values of this list to the end of the '
            "original list (default behavior for options of type `list+`)\n"
            '  - `"-"`: remove the values in this list from the original '
            "list (if present)\n"
            '  - `"prepend"`: prepend the values of this list to the '
            "beginning of the original list\n\n"
            "Some examples:\n"
            """
```toml
[cmake]
build_args = ["--verbose", "--clean-first"]
[linux.cmake]
build_args = ["--target", "foo"]
[windows.cmake]
build_args = {"-" = ["--verbose"], "+" = ["--target", "bar"]}
[macos.cmake]
build_args = {"=" = ["--target", "macos"]}
```
"""
            "Because `linux.cmake` inherits from `cmake`, and because "
            "`build_args` has type `list+`, this will result in a value of "
            '`["--verbose", "--clean-first", "--target", "foo"]` for the '
            "`linux.cmake.build_args` option. The value of "
            "`windows.cmake.build_args` will be "
            '`["--clean_first", "--target", "bar"]`, and the value of '
            '`macos.cmake.build_args` will be `["--target", "macos"]`.\n'
            """
```toml
[cmake]
config = ["Debug", "Release"]
[linux.cmake]
config = ["RelWithDebInfo"]
[windows.cmake]
config = {"prepend" = ["RelWithDebInfo"], "-" = ["Debug"], "+" = ["Debug"]}
```
"""
            "The `build_args` option has type `list`, so the value of "
            '`linux.cmake.config` is simply `["RelWithDebInfo"]`. The value '
            "of `windows.cmake.config` is "
            '`["RelWithDebInfo", "Release", "Debug"]`.\n\n'
            "The same rules also apply to CMake options:\n"
            """
```toml
[cmake.options]
CMAKE_PREFIX_PATH = "/some/path"
[linux.cmake.options]
CMAKE_PREFIX_PATH = {"prepend" = "/some/linux-specific/path"}
```
"""
            "This passes the option "
            "`-D CMAKE_PREFIX_PATH=/some/linux-specific/path;/some/path` to "
            "CMake."
        )


if __name__ == "__main__":
    cli()
