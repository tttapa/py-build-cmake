from . import __version__
from pathlib import Path
import click


def cmake_command(directory, build_path, verbose, dry, native, cross, local):

    def get_cmaker():
        from .build import _BuildBackend as backend
        from .datastructures import PackageInfo
        from .cmd_runner import CommandRunner
        source_dir = Path(directory or '.').resolve()
        config_settings = {
            "--cross": list(cross),
            "--local": list(local),
        }
        # Read configuration and package metadata
        cfg, pkg, metadata = backend.read_all_metadata(source_dir,
                                                       config_settings,
                                                       verbose)

        if not cfg.cmake:
            print("Not a CMake package")
            return None

        pkg_info = PackageInfo(
            version=metadata.version,
            package_name=cfg.package_name,
            module_name=cfg.module["name"],
        )
        # Select the right configuration (native build or cross build)
        cmake_cfg, native_cmake_cfg = backend.get_cmake_configs(cfg)
        cmake_cfg = native_cmake_cfg if native else cmake_cfg
        cross_cfg = None if native else cfg.cross
        # Override the build folder
        if build_path is not None:
            cmake_cfg['build_path'] = str(build_path)
        # Configure all CMake options
        return backend.get_cmaker(pkg_dir=source_dir,
                                  install_dir=None,
                                  cmake_cfg=cmake_cfg,
                                  cross_cfg=cross_cfg,
                                  native_install_dir=None,
                                  package_info=pkg_info,
                                  runner=CommandRunner(verbose=verbose,
                                                       dry=dry))

    return get_cmaker


@click.group()
@click.option("-C",
              "--directory",
              type=click.Path(exists=True, file_okay=False, dir_okay=True),
              required=False,
              help="The directory containing pyproject.toml.")
@click.option("-B",
              "--build-path",
              type=click.Path(exists=False, file_okay=False, dir_okay=True),
              required=False,
              default=None,
              help="Override py-build-cmake's default build folder.")
@click.option("-V",
              "--verbose",
              is_flag=True,
              help="Print verbose information about the commands being "
              "executed.")
@click.option("-n",
              "--dry",
              is_flag=True,
              help="Print the commands without actually invoking CMake.")
@click.option("--native",
              is_flag=True,
              help="When the configuration requests cross-compiling, "
              "configure for a native build instead. Has no effect otherwise.")
@click.option("--local",
              type=click.Path(exists=False, file_okay=True, dir_okay=False),
              required=False,
              multiple=True,
              help="Specifies a toml file that overrides the "
              "tool.py-build-cmake section of pyproject.toml, "
              "similar to py-build-cmake.local.toml.")
@click.option("--cross",
              type=click.Path(exists=False, file_okay=True, dir_okay=False),
              required=False,
              multiple=True,
              help="Specifies a toml file that overrides the "
              "tool.py-build-cmake.cross section of pyproject.toml, "
              "similar to py-build-cmake.cross.toml.")
@click.version_option(__version__, "-v", "--version")
@click.pass_context
def cli(ctx: click.Context, **kwargs):
    ctx.obj = cmake_command(**kwargs)


@cli.command(help="Configure the CMake project.")
@click.pass_obj
@click.option("--preset", nargs=1, type=str, required=False, metavar="PRESET")
@click.argument("args", nargs=-1, required=False)
def configure(obj, preset, args):
    cmaker = obj()
    if cmaker is None:
        return
    cmaker.conf_settings.args += args or []
    if preset is not None:
        cmaker.conf_settings.preset = preset
    cmaker.configure()


@cli.command(help="Build the CMake project.")
@click.pass_obj
@click.option("--preset",
              nargs=1,
              multiple=True,
              type=str,
              required=False,
              metavar="PRESET")
@click.option("--config",
              nargs=1,
              multiple=True,
              type=str,
              required=False,
              metavar="CONFIG")
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
@click.option("--preset",
              nargs=1,
              multiple=True,
              type=str,
              required=False,
              metavar="PRESET")
@click.option("--config",
              nargs=1,
              multiple=True,
              type=str,
              required=False,
              metavar="CONFIG")
@click.option("--component",
              nargs=1,
              multiple=True,
              type=str,
              required=False,
              metavar="COMP")
@click.argument("args", nargs=-1, required=False)
def install(obj, preset, config, component, args):
    cmaker = obj()
    if cmaker is None:
        return
    cmaker.install_settings.args += args or []
    if preset or config:
        cmaker.install_settings.presets = []
        cmaker.install_settings.configs = []
    if preset:
        cmaker.install_settings.presets = preset
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
@click.option("--component",
              is_flag=True,
              help="Documentation for the build_component backend.")
def format(md, component):
    from .pyproject_options import get_options, get_component_options
    from .config_options import pth
    if md:
        from .help import help_print_md as help_print
    else:
        from .help import help_print as help_print
    help_pth = pth('pyproject.toml/tool/py-build-cmake')
    pr_md = print if md else lambda *args, **kwargs: None
    pr_tx = lambda *args, **kwargs: None if md else print
    if component:
        pr_tx("List of py-build-cmake pyproject.toml options for the "
              "build_component backend:")
        pr_md("# py-build-cmake component build backend\n"
              "The `py_build_cmake.build_component` build backend allows "
              "building packages containing additional binaries that are not "
              "included with the main distribution.\n")
        pr_md("A possible use case is distributing debug symbols: these files "
              "can be large, and most users don't need them, so distributing "
              "them in a separate package makes sense.\n")
        pr_md(
            "See [examples/minimal-debug-component](https://github.com/tttapa/"
            "py-build-cmake/tree/main/examples/minimal-debug-component) "
            "for more information.\n"
        )
        help_print(get_component_options(Path('/'))[help_pth])

    else:
        pr_tx("List of py-build-cmake pyproject.toml options:")
        pr_md("# py-build-cmake configuration options\n")
        pr_md("These options go in the `[tool.py-build-cmake]` section of "
              "the `pyproject.toml` configuration file.\n")
        help_print(get_options(Path('/'))[help_pth])
        pr_md("# Local overrides\n")
        pr_md("Additionally, two extra configuration files can be placed in "
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
              "package without having to edit the main configuration file.\n")
        pr_md("# Command line overrides\n")
        pr_md("Instead of using the `py-build-cmake.local.toml` and "
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
              "instead.")


if __name__ == '__main__':
    cli()
