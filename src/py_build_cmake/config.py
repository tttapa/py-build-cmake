from dataclasses import dataclass, field
import re
import os
import warnings
from typing import Any, Dict, List, Optional, Set, cast
from pathlib import Path
from flit_core.config import ConfigError, read_pep621_metadata  # type: ignore
from distlib.util import normalize_name  # type: ignore

from .config_options import ConfigNode, OverrideConfigOption
from .pyproject_options import get_options, get_cross_path, get_tool_pbc_path, get_component_options

try:
    import tomllib as toml_  # type: ignore
except ImportError:
    import tomli as toml_  # type: ignore


@dataclass
class Config:
    dynamic_metadata: Set[str] = field(default_factory=set)
    entrypoints: Dict[str, Dict[str, str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    referenced_files: List[str] = field(default_factory=list)
    package_name: str = field(default='')
    module: Dict[str, str] = field(default_factory=dict)
    editable: Dict[str, Any] = field(default_factory=dict)
    sdist: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    license: Dict[str, str] = field(default_factory=dict)
    cmake: Optional[Dict[str, Any]] = field(default=None)
    stubgen: Optional[Dict[str, Any]] = field(default=None)
    cross: Optional[Dict[str, Any]] = field(default=None)


def read_config(pyproject_path, flag_overrides: Dict[str,
                                                     List[str]]) -> Config:
    # Load the pyproject.toml file
    pyproject_path = Path(pyproject_path)
    pyproject_folder = pyproject_path.parent
    pyproject = toml_.loads(pyproject_path.read_text('utf-8'))
    if 'project' not in pyproject:
        raise ConfigError('Missing [project] table')

    # Load local override
    localconfig_fname = 'py-build-cmake.local.toml'
    localconfig_path = pyproject_folder / localconfig_fname
    localconfig = None
    if localconfig_path.exists():
        localconfig = toml_.loads(localconfig_path.read_text('utf-8'))
        # treat empty local override as no local override
        localconfig = localconfig or None

    # Load override for cross-compilation
    crossconfig_fname = 'py-build-cmake.cross.toml'
    crossconfig_path = pyproject_folder / crossconfig_fname
    crossconfig = None
    if crossconfig_path.exists():
        crossconfig = toml_.loads(crossconfig_path.read_text('utf-8'))
        crossconfig = crossconfig or None

    # File names mapping to the actual dict with the config
    config_files = {
        "pyproject.toml": pyproject,
        localconfig_fname: localconfig,
        crossconfig_fname: crossconfig,
    }
    # Additional options for config_options
    extra_options: List[OverrideConfigOption] = []

    def try_load_local(path: Path):
        if not path.exists():
            raise FileNotFoundError(path.absolute())
        return toml_.loads(path.read_text('utf-8'))

    extra_flag_paths = {
        '--local': get_tool_pbc_path(),
        '--cross': get_cross_path(),
    }

    for flag, targetpath in extra_flag_paths.items():
        for path in map(Path, flag_overrides[flag]):
            if not path.is_absolute():
                path = (Path(os.environ.get("PWD", ".")) / path).resolve()
            extra_options.append(
                OverrideConfigOption(
                    str(path),
                    "Command line override flag",
                    targetpath=targetpath,
                ))
            config_files[str(path)] = try_load_local(path)

    return check_config(pyproject_path, pyproject, config_files, extra_options)


def check_config(pyproject_path, pyproject, config_files, extra_options):
    # Check the package/module name and normalize it
    f = 'name'
    if f in pyproject['project']:
        normname = normalize_name(pyproject['project'][f])
        if pyproject['project'][f] != normname:
            warnings.warn(
                f"Name changed from {pyproject['project'][f]} to {normname}")
        pyproject['project'][f] = normname

    # Parse the [project] section for metadata (using flit's parser)
    flit_cfg = read_pep621_metadata(pyproject['project'], pyproject_path)

    # Create our own config data structure using flit's output
    cfg = Config()
    cfg.dynamic_metadata = set(flit_cfg.dynamic_metadata)
    cfg.entrypoints = flit_cfg.entrypoints
    cfg.metadata = flit_cfg.metadata
    cfg.referenced_files = flit_cfg.referenced_files
    cfg.license = pyproject['project'].setdefault('license', {})
    cfg.package_name = normalize_name_wheel(cfg.metadata["name"])

    if 'file' in cfg.license and Path(cfg.license['file']).is_absolute():
        raise ConfigError("License path must be relative")

    opts = get_options(pyproject_path.parent)
    for o in extra_options:
        opts.insert(o)

    tree_config = ConfigNode.from_dict(config_files)
    opts.verify_all(tree_config)
    opts.override_all(tree_config)

    from .quirks.config import config_quirks
    tool_tree_cfg = tree_config[('pyproject.toml', 'tool', 'py-build-cmake')]
    config_quirks(tool_tree_cfg)

    set_up_os_specific_cross_inheritance(opts, tool_tree_cfg)
    opts.inherit_all(tree_config)
    opts.update_default_all(tree_config)
    dictcfg = cast(dict, tree_config.to_dict())
    tool_cfg = dictcfg['pyproject.toml']['tool']['py-build-cmake']

    # Store the module configuration
    s = 'module'
    if s in tool_cfg:
        # Normalize the import and wheel name of the package
        normname = normalize_name_wheel(tool_cfg[s]['name'])
        if tool_cfg[s]['name'] != normname:
            print(f"Name changed from {tool_cfg[s]['name']} to {normname}")
            # TODO: use logging instead of print
        tool_cfg[s]['name'] = normname
        cfg.module = tool_cfg[s]
    else:
        assert False, "Missing [tools.py-build-cmake.module] section"

    # Store the editable configuration
    cfg.editable = {
        os: tool_cfg[os]['editable']
        for os in ("linux", "windows", "mac", "cross")
        if os in tool_cfg and 'editable' in tool_cfg[os]
    }

    # Store the sdist folders (this is based on flit)
    def get_sdist_cludes(cfg):
        return {
            clude + '_patterns': cfg['sdist'][clude]
            for clude in ('include', 'exclude')
        }

    cfg.sdist = {
        os: get_sdist_cludes(tool_cfg[os])
        for os in ("linux", "windows", "mac", "cross")
        if os in tool_cfg
    }

    # Store the CMake configuration
    cfg.cmake = {
        os: tool_cfg[os]['cmake']
        for os in ("linux", "windows", "mac", "cross")
        if os in tool_cfg and 'cmake' in tool_cfg[os]
    }

    # Store stubgen configuration
    s = 'stubgen'
    if s in tool_cfg:
        cfg.stubgen = tool_cfg[s]

    # Store the cross compilation configuration
    s = 'cross'
    if s in tool_cfg:
        cfg.cross = tool_cfg[s]

    return cfg


def set_up_os_specific_cross_inheritance(opts, tool_tree_cfg):
    """Update the cross-compilation configuration to inherit from the
    corresponding OS configuration."""
    cross_os = None
    try:
        cross_os = tool_tree_cfg[('cross', 'os')].value
    except KeyError:
        pass
    if cross_os is not None:
        for s in ('cmake', 'sdist', 'editable'):
            inherit_from = get_tool_pbc_path() + (cross_os, s)
            print(opts[get_cross_path() + (s, )].inherit_from, '->', inherit_from)
            opts[get_cross_path() + (s, )].inherit_from = inherit_from


@dataclass
class ComponentConfig:
    dynamic_metadata: Set[str] = field(default_factory=set)
    entrypoints: Dict[str, Dict[str, str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    referenced_files: List[str] = field(default_factory=list)
    package_name: str = field(default='')
    component: Dict[str, Any] = field(default_factory=dict)
    license: Dict[str, str] = field(default_factory=dict)


def read_component_config(pyproject_path) -> ComponentConfig:
    # Load the pyproject.toml file
    pyproject_path = Path(pyproject_path)
    pyproject = toml_.loads(pyproject_path.read_text('utf-8'))
    if 'project' not in pyproject:
        raise ConfigError('Missing [project] table')

    # File names mapping to the actual dict with the config
    config_files = {
        "pyproject.toml": pyproject,
    }
    return check_component_config(pyproject_path, pyproject, config_files)


def check_component_config(pyproject_path, pyproject, config_files):
    # Check the package/module name and normalize it
    f = 'name'
    if f in pyproject['project']:
        normname = normalize_name(pyproject['project'][f])
        if pyproject['project'][f] != normname:
            warnings.warn(
                f"Name changed from {pyproject['project'][f]} to {normname}")
        pyproject['project'][f] = normname

    # Parse the [project] section for metadata (using flit's parser)
    flit_cfg = read_pep621_metadata(pyproject['project'], pyproject_path)

    # Create our own config data structure using flit's output
    cfg = ComponentConfig()
    cfg.dynamic_metadata = set(flit_cfg.dynamic_metadata)
    cfg.entrypoints = flit_cfg.entrypoints
    cfg.metadata = flit_cfg.metadata
    cfg.referenced_files = flit_cfg.referenced_files
    cfg.license = pyproject['project'].setdefault('license', {})
    cfg.package_name = normalize_name_wheel(cfg.metadata["name"])

    if 'file' in cfg.license and Path(cfg.license['file']).is_absolute():
        raise ConfigError("License path must be relative")

    opts = get_component_options(pyproject_path.parent)

    tree_config = ConfigNode.from_dict(config_files)
    opts.verify_all(tree_config)
    opts.override_all(tree_config)
    opts.inherit_all(tree_config)
    opts.update_default_all(tree_config)
    dictcfg = cast(dict, tree_config.to_dict())
    tool_cfg = dictcfg['pyproject.toml']['tool']['py-build-cmake']

    # Store the component configuration
    cfg.component = tool_cfg['component']

    return cfg


def normalize_name_wheel(name):
    """https://www.python.org/dev/peps/pep-0427/#escaping-and-unicode"""
    return re.sub(r"[^\w\d.]+", "_", name, re.UNICODE)
