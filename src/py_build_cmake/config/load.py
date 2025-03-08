from __future__ import annotations

import contextlib
import logging
import os
import pprint
import sys
from copy import copy
from dataclasses import fields
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional, cast

import pyproject_metadata
from distlib.util import normalize_name  # type: ignore[import-untyped]
from lark import LarkError

from .. import __version__
from ..common import ComponentConfig, Config, ConfigError
from ..common.platform import BuildPlatformInfo
from .cli_override import CLIOption, parse_cli, parse_file
from .options.config_path import ConfPath
from .options.config_reference import ConfigReference
from .options.default import ConfigDefaulter
from .options.finalize import ConfigFinalizer
from .options.inherit import ConfigInheritor
from .options.override import ConfigOverrider
from .options.pyproject_options import (
    get_component_options,
    get_component_path,
    get_cross_path,
    get_options,
    get_tool_pbc_path,
)
from .options.value_reference import OverrideAction, OverrideActionEnum, ValueReference
from .options.verify import ConfigVerifier
from .quirks import config_quirks

try:
    import tomllib as toml_  # type: ignore[import,unused-ignore]
except ImportError:
    import tomli as toml_  # type: ignore[import,no-redef,unused-ignore]

logger = logging.getLogger(__name__)

if sys.version_info < (3, 8):
    pp = pprint.pprint
else:
    pp = pprint.pp


def read_full_config(
    plat: BuildPlatformInfo,
    pyproject_path: Path,
    config_settings: dict[str, str | list[str]] | None,
    verbose: bool,
) -> Config:
    config_settings = config_settings or {}
    overrides, cli_overrides = parse_config_settings_overrides(config_settings, verbose)
    cfg = read_config(plat, pyproject_path, overrides, cli_overrides)
    if verbose:
        print_config_verbose(plat, cfg)
    return cfg


def parse_config_settings_overrides(
    config_settings: dict[str, str | list[str]], verbose: bool, component: bool = False
):
    if verbose:
        print("Configuration settings:")
        pp(config_settings)

    def listify(x: str | list[str]):
        return x if isinstance(x, list) else [x]

    def get_as_list(key: str):
        return listify(config_settings.get(key) or [])

    keys = ["component"] if component else ["local", "cross"]
    cli_overrides = (
        get_as_list("-o")
        + get_as_list("o")
        + get_as_list("override")
        + get_as_list("--override")
    )
    file_overrides = {key: get_as_list("--" + key) + get_as_list(key) for key in keys}
    if verbose:
        print("Configuration settings for local and cross-compilation file overrides:")
        pp(file_overrides)
        print("Configuration settings command-line overrides:")
        pp(cli_overrides)
    parsed_cli_overrides = []
    for o in cli_overrides:
        try:
            parsed_cli_overrides.append(parse_cli(o))
        except LarkError as e:
            msg = f"Failed to parse command line override: {o}"
            raise ConfigError(msg) from e
    return file_overrides, parsed_cli_overrides


def try_load_toml(path: Path):
    try:
        return toml_.loads(path.read_text("utf-8"))
    except FileNotFoundError as e:
        msg = f"Config file {str(path.absolute())!r} not found"
        raise ConfigError(msg) from e
    except OSError as e:
        msg = f"Config file {str(path.absolute())!r} could not be loaded"
        raise ConfigError(msg) from e
    except toml_.TOMLDecodeError as e:
        msg = f"Config file {str(path.absolute())!r} is invalid"
        raise ConfigError(msg) from e


def try_load_pbc(path: Path):
    try:
        return parse_file(path.read_text("utf-8"))
    except FileNotFoundError as e:
        msg = f"Config file {str(path.absolute())!r} not found"
        raise ConfigError(msg) from e
    except OSError as e:
        msg = f"Config file {str(path.absolute())!r} could not be loaded"
        raise ConfigError(msg) from e
    except LarkError as e:
        msg = f"Config file {str(path.absolute())!r} is invalid"
        raise ConfigError(msg) from e


def load_extra_config_files(flag_overrides, targetpath, config_files, overrides):
    for path in map(Path, flag_overrides):
        if path.is_absolute():
            fullpath = path
        else:
            fullpath = (Path(os.environ.get("PWD", ".")) / path).resolve()
        if path.suffix == ".toml":
            config = try_load_toml(fullpath)
            if config:  # Treat empty file as no override
                config_files[fullpath.as_posix()] = config
                overrides[ConfPath((fullpath.as_posix(),))] = targetpath
        elif path.suffix == ".pbc":
            options = try_load_pbc(fullpath)
            for i, o in enumerate(options):
                label = f"{fullpath.as_posix()}[{i+1}]"
                override = add_cli_override(config_files, o, label, targetpath)
                overrides.update(override)
        else:
            msg = f"Config file {str(path.absolute())!r} "
            msg += "has an unsupported extension (should be .toml or .pbc)"
            raise ConfigError(msg)


def read_config(
    plat: BuildPlatformInfo,
    pyproject_path: str | Path,
    flag_overrides: dict[str, list[str]],
    cli_overrides: list[CLIOption],
) -> Config:
    # Load the pyproject.toml file
    pyproject_path = Path(pyproject_path)
    pyproject_folder = pyproject_path.parent
    pyproject: dict[str, Any] = try_load_toml(pyproject_path)
    if "project" not in pyproject:
        msg = "Missing [project] table"
        raise ConfigError(msg)

    # Load local overrides
    check_if_local_configs_exist(flag_overrides, pyproject_folder)

    # File names mapping to the actual dict with the config
    config_files: dict[str, dict[str, Any]] = {
        "pyproject.toml": pyproject,
    }

    # Additional options for config_options
    overrides: dict[ConfPath, ConfPath] = {}
    # What to override
    extra_flag_paths = {"local": get_tool_pbc_path(), "cross": get_cross_path()}

    # Files specified on the command line
    for flag, targetpath in extra_flag_paths.items():
        load_extra_config_files(
            flag_overrides[flag], targetpath, config_files, overrides
        )

    # Command-line overrides
    for i, o in enumerate(cli_overrides):
        overrides.update(add_cli_override(config_files, o, f"<cli:{i+1}>"))

    return process_config(plat, pyproject_path, config_files, overrides)


def check_if_local_configs_exist(flag_overrides, pyproject_folder):
    localconfig_path = pyproject_folder / "py-build-cmake.local.pbc"
    if localconfig_path.exists():
        flag_overrides.setdefault("local", []).insert(0, str(localconfig_path))
    localconfig_path = localconfig_path.with_suffix(".toml")
    if localconfig_path.exists():
        flag_overrides.setdefault("local", []).insert(0, str(localconfig_path))
    # Load override for cross-compilation
    crossconfig_path = pyproject_folder / "py-build-cmake.cross.pbc"
    if crossconfig_path.exists():
        flag_overrides.setdefault("cross", []).insert(0, str(crossconfig_path))
    crossconfig_path = crossconfig_path.with_suffix(".toml")
    if crossconfig_path.exists():
        flag_overrides.setdefault("cross", []).insert(0, str(crossconfig_path))


def add_cli_override(
    config_files: dict[str, dict[str, Any]],
    opt: CLIOption,
    label: str,
    targetpath: ConfPath | None = None,
):
    if targetpath is None:
        targetpath = get_tool_pbc_path()
    overrides = {ConfPath((label,)): targetpath}
    o: dict = config_files.setdefault(label, {})
    for k in opt.key[:-1]:
        o = o.setdefault(k, {})
    o[opt.key[-1]] = OverrideAction(
        action=OverrideActionEnum(opt.action), values=opt.value
    )
    return overrides


def check_pyproject(config_files: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pyproject = config_files["pyproject.toml"]
    assert pyproject is not None
    # Make sure that project section exists
    project = pyproject.get("project")
    if project is None:
        msg = "Missing [project] section in pyproject.toml"
        raise ConfigError(msg)
    # Check the package/module name and normalize it
    f = "name"
    if f in project:
        oldname = project[f]
        normname = normalize_name(oldname)
        if oldname != normname:
            logger.info("Name normalized from %s to %s", oldname, normname)
        project[f] = normname
    # Initialize the tool section
    pyproject.setdefault("tool", {}).setdefault("py-build-cmake", {})
    return pyproject


def process_config(
    plat: BuildPlatformInfo,
    pyproject_path: Path | PurePosixPath,
    config_files: dict[str, dict[str, Any]],
    overrides: dict[ConfPath, ConfPath],
    test: bool = False,
) -> Config:

    # Parse the [project] section for metadata
    pyproject = check_pyproject(config_files)
    try:
        Metadata = pyproject_metadata.StandardMetadata
        meta = Metadata.from_pyproject(pyproject, pyproject_path.parent)
    except pyproject_metadata.ConfigurationError as e:
        raise ConfigError(str(e)) from e

    # Create our own config data structure
    cfg = Config(meta)
    cfg.package_name = meta.name

    # py-build-cmake option tree
    opts = get_options(pyproject_path.parent, test=test)
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), config_files)

    # Verify the configuration and apply the overrides
    verify_and_override_config(overrides, root_ref, root_val)

    # Tweak the configuration depending on the environment and platform
    config_quirks(plat, root_val.sub_ref(get_tool_pbc_path()))
    set_up_os_specific_cross_inheritance(root_ref, root_val)

    # Carry out inheritance between options
    inherit_default_and_finalize_config(root_ref, root_val)
    pbc_value_ref = root_val.sub_ref(get_tool_pbc_path())

    # Store the module configuration
    s = "module"
    if pbc_value_ref.is_value_set(s):
        # Normalize the import and wheel name of the package
        name_path = ConfPath((s, "name"))
        name = cast(str, pbc_value_ref.get_value(name_path))
        normname = name.replace("-", "_")
        pbc_value_ref.set_value(name_path, normname)
        cfg.module = pbc_value_ref.get_value(s)
    else:
        msg = "Missing [tools.py-build-cmake.module] section"
        raise AssertionError(msg)

    # Store the editable configuration
    cfg.editable = {
        os: cast(Dict[str, Any], pbc_value_ref.get_value(ConfPath((os, "editable"))))
        for os in ("linux", "windows", "mac", "pyodide", "cross")
        if pbc_value_ref.is_value_set(ConfPath((os, "editable")))
    }

    # Store the sdist folders (this is based on flit)
    def get_sdist_cludes(v: ValueReference) -> dict[str, Any]:
        return {
            clude + "_patterns": v.get_value(ConfPath(("sdist", clude)))
            for clude in ("include", "exclude")
        }

    cfg.sdist = {
        os: get_sdist_cludes(pbc_value_ref.sub_ref(os))
        for os in ("linux", "windows", "mac", "pyodide", "cross")
        if pbc_value_ref.is_value_set(os)
    }

    # Store the CMake configuration
    cfg.cmake = {
        os: cast(Dict[str, Any], pbc_value_ref.get_value(ConfPath((os, "cmake"))))
        for os in ("linux", "windows", "mac", "pyodide", "cross")
        if pbc_value_ref.is_value_set(ConfPath((os, "cmake")))
    }
    cfg.cmake = cfg.cmake or None

    # Store the Wheel configuration
    cfg.wheel = {
        os: cast(Dict[str, Any], pbc_value_ref.get_value(ConfPath((os, "wheel"))))
        for os in ("linux", "windows", "mac", "pyodide", "cross")
        if pbc_value_ref.is_value_set(ConfPath((os, "wheel")))
    }

    # Store stubgen configuration
    s = "stubgen"
    if pbc_value_ref.is_value_set(s):
        cfg.stubgen = pbc_value_ref.get_value(s)

    # Store the cross compilation configuration
    s = "cross"
    if pbc_value_ref.is_value_set(s):
        cfg.cross = copy(cast(Optional[Dict[str, Any]], pbc_value_ref.get_value(s)))
        if cfg.cross is not None:
            for k in ("cmake", "wheel", "sdist", "editable"):
                cfg.cross.pop(k, None)

    # Check for incompatible options
    cfg.check()

    return cfg


def verify_and_override_config(
    overrides: dict[ConfPath, ConfPath],
    root_ref: ConfigReference,
    root_val: ValueReference,
):
    root_val.set_value(
        "pyproject.toml",
        ConfigVerifier(
            root=root_ref,
            ref=root_ref.sub_ref("pyproject.toml"),
            values=root_val.sub_ref("pyproject.toml"),
        ).verify(),
    )
    for override, target in overrides.items():
        root_val.set_value(
            override,
            ConfigVerifier(
                root=root_ref,
                ref=root_ref.sub_ref(target),
                values=root_val.sub_ref(override),
            ).verify(),
        )
        root_val.set_value_default(target, {})
        root_val.set_value(
            target,
            ConfigOverrider(
                root=root_ref,
                ref=root_ref.sub_ref(target),
                values=root_val.sub_ref(target),
                new_values=root_val.sub_ref(override),
            ).override(),
        )


def inherit_default_and_finalize_config(
    root_ref: ConfigReference, root_val: ValueReference
):
    ConfigInheritor(
        root=root_ref,
        root_values=root_val,
    ).inherit()
    root_val.set_value(
        "pyproject.toml",
        ConfigFinalizer(
            root=root_ref,
            ref=root_ref.sub_ref("pyproject.toml"),
            values=root_val.sub_ref("pyproject.toml"),
        ).finalize(),
    )
    ConfigDefaulter(
        root=root_ref,
        root_values=root_val,
        ref=root_ref.sub_ref("pyproject.toml"),
        value_path=ConfPath.from_string("pyproject.toml"),
    ).update_default()


def set_up_os_specific_cross_inheritance(
    root_ref: ConfigReference, root_val: ValueReference
):
    """Update the cross-compilation configuration to inherit from the
    corresponding OS-specific configuration."""
    cross_os = None
    with contextlib.suppress(KeyError):
        os_path = get_tool_pbc_path().join("cross").join("os")
        cross_os = cast(Optional[str], root_val.get_value(os_path))

    if cross_os is not None:
        for s in ("editable", "sdist", "cmake", "wheel"):
            parent = get_tool_pbc_path().join(cross_os).join(s)
            child = get_cross_path().join(s)
            root_ref.sub_ref(child).config.inherits = parent


def print_config_verbose(plat: BuildPlatformInfo, cfg: Config):
    print("\npy-build-cmake (" + __version__ + ")")
    print()
    print("platform")
    print("================================")
    for f in fields(plat):
        print(f.name, end=": ")
        pp(getattr(plat, f.name))
    print("platform_tag", end=": ")
    pp(plat.platform_tag)
    print("================================\n")
    print("options")
    print("================================")
    print("package_name:")
    print(repr(cfg.package_name))
    print("module:")
    pp(cfg.module)
    print("editable:")
    pp(cfg.editable)
    print("sdist:")
    pp(cfg.sdist)
    print("cmake:")
    pp(cfg.cmake)
    print("wheel:")
    pp(cfg.wheel)
    print("cross:")
    pp(cfg.cross)
    print("stubgen:")
    pp(cfg.stubgen)
    print("================================\n")


def read_full_component_config(
    plat: BuildPlatformInfo,
    pyproject_path: Path,
    config_settings: dict[str, str | list[str]] | None,
    verbose: bool,
) -> ComponentConfig:
    config_settings = config_settings or {}
    overrides, cli_overrides = parse_config_settings_overrides(
        config_settings, verbose, component=True
    )
    cfg = read_component_config(pyproject_path, overrides, cli_overrides)
    if cfg.standard_metadata.dynamic:
        msg = "Dynamic metadata not supported for components."
        raise ConfigError(msg)
    if verbose:
        print_component_config_verbose(cfg)
    return cfg


def read_component_config(
    pyproject_path: Path,
    flag_overrides: dict[str, list[str]],
    cli_overrides: list[CLIOption],
) -> ComponentConfig:
    # Load the pyproject.toml file
    pyproject_folder = pyproject_path.parent
    pyproject: dict[str, Any] = try_load_toml(pyproject_path)
    if "project" not in pyproject:
        msg = "Missing [project] table"
        raise ConfigError(msg)

    # Load local overrides
    check_if_local_configs_exist(flag_overrides, pyproject_folder)

    # File names mapping to the actual dict with the config
    config_files: dict[str, dict[str, Any]] = {
        "pyproject.toml": pyproject,
    }

    # Additional options for config_options
    overrides: dict[ConfPath, ConfPath] = {}
    # What to override
    extra_flag_paths = {"component": get_component_path()}

    # Files specified on the command line
    for flag, targetpath in extra_flag_paths.items():
        load_extra_config_files(
            flag_overrides[flag], targetpath, config_files, overrides
        )

    # Command-line overrides
    for i, o in enumerate(cli_overrides):
        overrides.update(add_cli_override(config_files, o, f"<cli:{i+1}>"))

    return process_component_config(pyproject_path, pyproject, overrides, config_files)


def process_component_config(
    pyproject_path: Path,
    pyproject: dict[str, Any],
    overrides: dict[ConfPath, ConfPath],
    config_files: dict[str, dict[str, Any]],
):
    # Check the package/module name and normalize it
    f = "name"
    if f in pyproject["project"]:
        oldname = pyproject["project"][f]
        normname = normalize_name(oldname)
        if oldname != normname:
            logger.info("Name normalized from %s to %s", oldname, normname)
        pyproject["project"][f] = normname

        # Parse the [project] section for metadata
    try:
        meta = pyproject_metadata.StandardMetadata.from_pyproject(
            pyproject, pyproject_path.parent
        )
    except pyproject_metadata.ConfigurationError as e:
        raise ConfigError(str(e)) from e

    # py-build-cmake option tree
    opts = get_component_options(pyproject_path.parent)
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), config_files)

    # Verify the configuration and apply the overrides
    verify_and_override_config(overrides, root_ref, root_val)

    # Carry out inheritance between options
    inherit_default_and_finalize_config(root_ref, root_val)
    pbc_value_ref = root_val.sub_ref(get_tool_pbc_path())

    # Store the component configuration
    main_project = pbc_value_ref.get_value("main_project")
    assert isinstance(main_project, Path)
    cfg = ComponentConfig(meta, main_project)
    cfg.package_name = meta.name
    cfg.component = pbc_value_ref.get_value("component")

    return cfg


def print_component_config_verbose(cfg: ComponentConfig):
    print("\npy-build-cmake (" + __version__ + ")")
    print("options")
    print("================================")
    print("package_name:")
    print(repr(cfg.package_name))
    print("main_project:")
    print(repr(cfg.main_project.as_posix()))
    print("component:")
    pp(cfg.component)
    print("================================\n")
