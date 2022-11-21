from . import __version__
from pathlib import Path
import click


def cmake_command(directory, verbose, dry, native, cross, local):

    def get_cmaker():
        from .build import _BuildBackend as backend
        from .datastructures import PackageInfo
        source_dir = Path(directory or '.').resolve()
        config_settings = {
            "--cross": cross,
            "--local": local,
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
        # Configure all CMake options
        return backend.get_cmaker(pkg_dir=source_dir,
                                  install_dir=None,
                                  cmake_cfg=cmake_cfg,
                                  cross_cfg=cross_cfg,
                                  native_install_dir=None,
                                  package_info=pkg_info,
                                  verbose=verbose,
                                  dry=dry)

    return get_cmaker


@click.group()
@click.option("-C",
              "--directory",
              type=click.Path(exists=True, file_okay=False, dir_okay=True),
              required=False,
              help="The directory containing pyproject.toml.")
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
              help="Specifies a toml file that overrides the "
              "`tool.py-build-cmake` section of `pyproject.toml`, "
              "similar to `py-build-cmake.local.toml`.")
@click.option("--cross",
              type=click.Path(exists=False, file_okay=True, dir_okay=False),
              required=False,
              help="Specifies a toml file that overrides the "
              "`tool.py-build-cmake.cross` section of `pyproject.toml`, "
              "similar to `py-build-cmake.cross.toml`.")
@click.version_option(__version__, "-v", "--version")
@click.pass_context
def cli(ctx: click.Context, **kwargs):
    ctx.obj = cmake_command(**kwargs)


@cli.command(help="Configure the CMake project.")
@click.pass_obj
@click.option("--preset", nargs=1, type=str, required=False)
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
@click.option("--preset", nargs=1, multiple=True, type=str, required=False)
@click.option("--config", nargs=1, multiple=True, type=str, required=False)
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
@click.option("--preset", nargs=1, multiple=True, type=str, required=False)
@click.option("--config", nargs=1, multiple=True, type=str, required=False)
@click.option("--component", nargs=1, multiple=True, type=str, required=False)
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
def format(md):
    from .pyproject_options import get_options
    from .config_options import pth
    opts = get_options(Path('/'))
    help_pth = pth('pyproject.toml/tool/py-build-cmake')
    pbc_opts = opts[help_pth]
    if md:
        from .help import help_print_md as help_print
    else:
        from .help import help_print as help_print
    help_print(pbc_opts)


if __name__ == '__main__':
    cli()
