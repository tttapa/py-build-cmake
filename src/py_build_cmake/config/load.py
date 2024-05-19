from __future__ import annotations

import contextlib
import logging
import os
from copy import copy
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from pprint import pprint
from typing import Any, Dict, Optional, cast

import pyproject_metadata
from distlib.util import normalize_name  # type: ignore[import-untyped]

from .. import __version__
from ..common import Config, ConfigError
from .options.config_path import ConfPath
from .options.config_reference import ConfigReference
from .options.default import ConfigDefaulter
from .options.finalize import ConfigFinalizer
from .options.inherit import ConfigInheritor
from .options.override import ConfigOverrider
from .options.pyproject_options import (
    get_component_options,
    get_cross_path,
    get_options,
    get_tool_pbc_path,
)
from .options.value_reference import ValueReference
from .options.verify import ConfigVerifier
from .quirks import config_quirks

try:
    import tomllib as toml_  # type: ignore[import,unused-ignore]
except ImportError:
    import tomli as toml_  # type: ignore[import,no-redef,unused-ignore]

logger = logging.getLogger(__name__)


def read_full_config(
    pyproject_path: Path,
    config_settings: dict[str, str | list[str]] | None,
    verbose: bool,
) -> Config:
    config_settings = config_settings or {}
    overrides = parse_config_settings_overrides(config_settings, verbose)
    cfg = read_config(pyproject_path, overrides)
    if verbose:
        print_config_verbose(cfg)
    return cfg


def parse_config_settings_overrides(
    config_settings: dict[str, str | list[str]], verbose: bool
):
    if verbose:
        print("Configuration settings:")
        pprint(config_settings)

    def listify(x: str | list[str]):
        return x if isinstance(x, list) else [x]

    def get_as_list(key: str):
        return listify(config_settings.get(key) or [])

    keys = ["local", "cross"]
    overrides = {key: get_as_list("--" + key) + get_as_list(key) for key in keys}
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


def read_config(
    pyproject_path: str | Path, flag_overrides: dict[str, list[str]]
) -> Config:
    # Load the pyproject.toml file
    pyproject_path = Path(pyproject_path)
    pyproject_folder = pyproject_path.parent
    pyproject: dict[str, Any] = try_load_toml(pyproject_path)
    if "project" not in pyproject:
        msg = "Missing [project] table"
        raise ConfigError(msg)

    # Load local override
    localconfig_path = pyproject_folder / "py-build-cmake.local.toml"
    if localconfig_path.exists():
        flag_overrides.setdefault("local", []).insert(0, str(localconfig_path))
    # Load override for cross-compilation
    crossconfig_path = pyproject_folder / "py-build-cmake.cross.toml"
    if crossconfig_path.exists():
        flag_overrides.setdefault("cross", []).insert(0, str(crossconfig_path))

    # File names mapping to the actual dict with the config
    config_files: dict[str, dict[str, Any]] = {
        "pyproject.toml": pyproject,
        "<command-line>": {},  # FIXME: implement this
    }

    # Additional options for config_options
    overrides: dict[ConfPath, ConfPath] = {}
    # What to override
    extra_flag_paths = {"local": get_tool_pbc_path(), "cross": get_cross_path()}

    for flag, targetpath in extra_flag_paths.items():
        for path in map(Path, flag_overrides[flag]):
            if path.is_absolute():
                fullpath = path
            else:
                fullpath = (Path(os.environ.get("PWD", ".")) / path).resolve()
            config = try_load_toml(fullpath)
            if config:  # Treat empty file as no override
                config_files[fullpath.as_posix()] = config
                overrides[ConfPath((fullpath.as_posix(),))] = targetpath

    return process_config(pyproject_path, config_files, overrides)


def process_config(
    pyproject_path: Path | PurePosixPath,
    config_files: dict[str, dict[str, Any]],
    overrides: dict[ConfPath, ConfPath],
    test: bool = False,
) -> Config:
    pyproject = config_files["pyproject.toml"]
    assert pyproject is not None
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

    # py-build-cmake option tree
    opts = get_options(pyproject_path.parent, test=test)
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), config_files)

    # Verify the configuration and apply the overrides
    verify_and_override_config(overrides, root_ref, root_val)

    # Tweak the configuration depending on the environment and platform
    config_quirks(root_val.sub_ref(get_tool_pbc_path()))
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
        for os in ("linux", "windows", "mac", "cross")
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
        for os in ("linux", "windows", "mac", "cross")
        if pbc_value_ref.is_value_set(os)
    }

    # Store the CMake configuration
    cfg.cmake = {
        os: cast(Dict[str, Any], pbc_value_ref.get_value(ConfPath((os, "cmake"))))
        for os in ("linux", "windows", "mac", "cross")
        if pbc_value_ref.is_value_set(ConfPath((os, "cmake")))
    }
    cfg.cmake = cfg.cmake or None

    # Store stubgen configuration
    s = "stubgen"
    if pbc_value_ref.is_value_set(s):
        cfg.stubgen = pbc_value_ref.get_value(s)

    # Store the cross compilation configuration
    s = "cross"
    if pbc_value_ref.is_value_set(s):
        cfg.cross = copy(cast(Optional[Dict[str, Any]], pbc_value_ref.get_value(s)))
        if cfg.cross is not None:
            for k in ("cmake", "sdist", "editable"):
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
    ConfigDefaulter(
        root=root_ref,
        root_values=root_val,
        ref=root_ref.sub_ref("pyproject.toml"),
        value_path=ConfPath.from_string("pyproject.toml"),
    ).update_default()
    root_val.set_value(
        "pyproject.toml",
        ConfigFinalizer(
            root=root_ref,
            ref=root_ref.sub_ref("pyproject.toml"),
            values=root_val.sub_ref("pyproject.toml"),
        ).finalize(),
    )


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
        for s in ("cmake", "sdist", "editable"):
            parent = get_tool_pbc_path().join(cross_os).join(s)
            child = get_cross_path().join(s)
            root_ref.sub_ref(child).config.inherits = parent


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
    pyproject_path: Path, config_settings: dict[str, list[Any]] | None, verbose: bool
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
    config_files: dict[str, dict[str, Any]] = {
        "pyproject.toml": pyproject,
    }
    return process_component_config(pyproject_path, pyproject, config_files)


def process_component_config(
    pyproject_path: Path,
    pyproject: dict[str, Any],
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

    # Create our own config data structure
    cfg = ComponentConfig(meta)
    cfg.package_name = meta.name

    # py-build-cmake option tree
    opts = get_component_options(pyproject_path.parent)
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), config_files)

    # Verify the configuration and apply the overrides
    root_val.set_value(
        "pyproject.toml",
        ConfigVerifier(
            root=root_ref,
            ref=root_ref.sub_ref("pyproject.toml"),
            values=root_val.sub_ref("pyproject.toml"),
        ).verify(),
    )
    # Carry out inheritance between options
    ConfigInheritor(
        root=root_ref,
        root_values=root_val,
    ).inherit()
    ConfigDefaulter(
        root=root_ref,
        root_values=root_val,
        ref=root_ref.sub_ref("pyproject.toml"),
        value_path=ConfPath.from_string("pyproject.toml"),
    ).update_default()
    root_val.set_value(
        "pyproject.toml",
        ConfigFinalizer(
            root=root_ref,
            ref=root_ref.sub_ref("pyproject.toml"),
            values=root_val.sub_ref("pyproject.toml"),
        ).finalize(),
    )
    pbc_value_ref = root_val.sub_ref(get_tool_pbc_path())

    # Store the component configuration
    cfg.component = pbc_value_ref.get_value("component")

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
