from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from pprint import pprint
from typing import Any, cast

import pyproject_metadata
from distlib.util import normalize_name  # type: ignore[import-untyped]

from .. import __version__
from ..common import Config, ConfigError
from .config_options import ConfigNode, OverrideConfigOption
from .pyproject_options import (
    get_component_options,
    get_cross_path,
    get_options,
    get_tool_pbc_path,
)
from .quirks import config_quirks

try:
    import tomllib as toml_  # type: ignore[import,unused-ignore]
except ImportError:
    import tomli as toml_  # type: ignore[import,no-redef,unused-ignore]

logger = logging.getLogger(__name__)


def read_full_config(
    pyproject_path: Path, config_settings: dict | None, verbose: bool
) -> Config:
    config_settings = config_settings or {}
    overrides = parse_config_settings_overrides(config_settings, verbose)
    cfg = read_config(pyproject_path, overrides)
    if verbose:
        print_config_verbose(cfg)
    return cfg


def parse_config_settings_overrides(config_settings: dict, verbose: bool):
    if verbose:
        print("Configuration settings:")
        pprint(config_settings)
    listify = lambda x: x if isinstance(x, list) else [x]
    keys = ["--local", "--cross"]
    overrides = {key: listify(config_settings.get(key) or []) for key in keys}
    if verbose:
        print("Configuration settings for local and cross-compilation overrides:")
        pprint(overrides)
    return overrides


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


def read_config(pyproject_path, flag_overrides: dict[str, list[str]]) -> Config:
    # Load the pyproject.toml file
    pyproject_path = Path(pyproject_path)
    pyproject_folder = pyproject_path.parent
    pyproject = try_load_toml(pyproject_path)
    if "project" not in pyproject:
        msg = "Missing [project] table"
        raise ConfigError(msg)

    # Load local override
    localconfig_fname = "py-build-cmake.local.toml"
    localconfig_path = pyproject_folder / localconfig_fname
    localconfig = None
    if localconfig_path.exists():
        localconfig = try_load_toml(localconfig_path)
        # treat empty local override as no local override
        localconfig = localconfig or None

    # Load override for cross-compilation
    crossconfig_fname = "py-build-cmake.cross.toml"
    crossconfig_path = pyproject_folder / crossconfig_fname
    crossconfig = None
    if crossconfig_path.exists():
        crossconfig = try_load_toml(crossconfig_path)
        crossconfig = crossconfig or None

    # File names mapping to the actual dict with the config
    config_files = {
        "pyproject.toml": pyproject,
        localconfig_fname: localconfig,
        crossconfig_fname: crossconfig,
    }
    # Additional options for config_options
    extra_options: list[OverrideConfigOption] = []

    extra_flag_paths = {
        "--local": get_tool_pbc_path(),
        "--cross": get_cross_path(),
    }

    for flag, targetpath in extra_flag_paths.items():
        for path in map(Path, flag_overrides[flag]):
            if path.is_absolute():
                fullpath = path
            else:
                fullpath = (Path(os.environ.get("PWD", ".")) / path).resolve()
            extra_options.append(
                OverrideConfigOption(
                    str(fullpath),
                    "Command line override flag",
                    targetpath=targetpath,
                )
            )
            config_files[str(fullpath)] = try_load_toml(fullpath)

    return process_config(pyproject_path, config_files, extra_options)


def process_config(
    pyproject_path: Path,
    config_files: dict,
    extra_options: list[OverrideConfigOption],
    test: bool = False,
) -> Config:
    pyproject = config_files["pyproject.toml"]
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
        Metadata = pyproject_metadata.StandardMetadata
        meta = Metadata.from_pyproject(pyproject, pyproject_path.parent)
    except pyproject_metadata.ConfigurationError as e:
        raise ConfigError(str(e)) from e

    # Create our own config data structure
    cfg = Config(meta)
    cfg.package_name = meta.name

    # Additional options from command-line overrides
    opts = get_options(pyproject_path.parent, test=test)
    for o in extra_options:
        opts.insert(o)

    # Verify the configuration and apply the overrides
    tree_config = ConfigNode.from_dict(config_files)
    opts.verify_all(tree_config)
    opts.override_all(tree_config)

    # Tweak the configuration depending on the environment and platform
    tool_tree_cfg = tree_config[("pyproject.toml", "tool", "py-build-cmake")]
    config_quirks(tool_tree_cfg)

    set_up_os_specific_cross_inheritance(opts, tool_tree_cfg)
    opts.inherit_all(tree_config)
    opts.update_default_all(tree_config)
    dictcfg = cast(dict, tree_config.to_dict())
    tool_cfg = dictcfg["pyproject.toml"]["tool"]["py-build-cmake"]

    # Store the module configuration
    s = "module"
    if s in tool_cfg:
        # Normalize the import and wheel name of the package
        normname = tool_cfg[s]["name"].replace("-", "_")
        tool_cfg[s]["name"] = normname
        cfg.module = tool_cfg[s]
    else:
        msg = "Missing [tools.py-build-cmake.module] section"
        raise AssertionError(msg)

    # Store the editable configuration
    cfg.editable = {
        os: tool_cfg[os]["editable"]
        for os in ("linux", "windows", "mac", "cross")
        if os in tool_cfg and "editable" in tool_cfg[os]
    }

    # Store the sdist folders (this is based on flit)
    def get_sdist_cludes(cfg):
        return {
            clude + "_patterns": cfg["sdist"][clude] for clude in ("include", "exclude")
        }

    cfg.sdist = {
        os: get_sdist_cludes(tool_cfg[os])
        for os in ("linux", "windows", "mac", "cross")
        if os in tool_cfg
    }

    # Store the CMake configuration
    cfg.cmake = {
        os: tool_cfg[os]["cmake"]
        for os in ("linux", "windows", "mac", "cross")
        if os in tool_cfg and "cmake" in tool_cfg[os]
    }
    cfg.cmake = cfg.cmake or None

    # Store stubgen configuration
    s = "stubgen"
    if s in tool_cfg:
        cfg.stubgen = tool_cfg[s]

    # Store the cross compilation configuration
    s = "cross"
    if s in tool_cfg:
        cfg.cross = tool_cfg[s]

    # Check for incompatible options
    cfg.check()

    return cfg


def set_up_os_specific_cross_inheritance(opts, tool_tree_cfg):
    """Update the cross-compilation configuration to inherit from the
    corresponding OS configuration."""
    cross_os = None
    with contextlib.suppress(KeyError):
        cross_os = tool_tree_cfg[("cross", "os")].value

    if cross_os is not None:
        for s in ("cmake", "sdist", "editable"):
            inherit_from = (*get_tool_pbc_path(), cross_os, s)
            opts[(*get_cross_path(), s)].inherit_from = inherit_from


def print_config_verbose(cfg: Config):
    print("\npy-build-cmake (" + __version__ + ")")
    print("options")
    print("================================")
    print("package_name:")
    print(repr(cfg.package_name))
    print("module:")
    pprint(cfg.module)
    print("editable:")
    pprint(cfg.editable)
    print("sdist:")
    pprint(cfg.sdist)
    print("cmake:")
    pprint(cfg.cmake)
    print("cross:")
    pprint(cfg.cross)
    print("stubgen:")
    pprint(cfg.stubgen)
    print("================================\n")


@dataclass
class ComponentConfig:
    standard_metadata: pyproject_metadata.StandardMetadata
    package_name: str = field(default="")
    component: dict[str, Any] = field(default_factory=dict)


def read_full_component_config(
    pyproject_path: Path, config_settings: dict | None, verbose: bool
) -> ComponentConfig:
    config_settings = config_settings or {}
    cfg = read_component_config(pyproject_path)
    if cfg.standard_metadata.dynamic:
        msg = "Dynamic metadata not supported for components."
        raise ConfigError(msg)
    if verbose:
        print_component_config_verbose(cfg)
    return cfg


def read_component_config(pyproject_path: Path) -> ComponentConfig:
    # Load the pyproject.toml file
    pyproject = try_load_toml(pyproject_path)
    if "project" not in pyproject:
        msg = "Missing [project] table"
        raise ConfigError(msg)

    # File names mapping to the actual dict with the config
    config_files = {
        "pyproject.toml": pyproject,
    }
    return process_component_config(pyproject_path, pyproject, config_files)


def process_component_config(pyproject_path: Path, pyproject, config_files):
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

    # Create our own config data structure
    cfg = ComponentConfig(meta)
    cfg.package_name = meta.name

    opts = get_component_options(pyproject_path.parent)

    tree_config = ConfigNode.from_dict(config_files)
    opts.verify_all(tree_config)
    opts.override_all(tree_config)
    opts.inherit_all(tree_config)
    opts.update_default_all(tree_config)
    dictcfg = cast(dict, tree_config.to_dict())
    tool_cfg = dictcfg["pyproject.toml"]["tool"]["py-build-cmake"]

    # Store the component configuration
    cfg.component = tool_cfg["component"]

    return cfg


def print_component_config_verbose(cfg: ComponentConfig):
    print("\npy-build-cmake (" + __version__ + ")")
    print("options")
    print("================================")
    print("package_name:")
    print(repr(cfg.package_name))
    print("component:")
    pprint(cfg.component)
    print("================================\n")
