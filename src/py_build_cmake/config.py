from dataclasses import dataclass, field
import re
import warnings
import tomli
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from flit_core.config import ConfigError, read_pep621_metadata
from flit_core.config import _check_glob_patterns
from distlib.util import normalize_name

from .config_options import ConfigNode, OverrideConfigOption
from .pyproject_options import get_options, get_cross_path, get_tool_pbc_path


@dataclass
class Config:
    dynamic_metadata: Set[str] = field(default_factory=set)
    entrypoints: Dict[str, Dict[str, str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    referenced_files: List[str] = field(default_factory=list)
    module: Dict[str, str] = field(default_factory=dict)
    sdist: Dict[str, List[str]] = field(default_factory=dict)
    license: Dict[str, str] = field(default_factory=dict)
    cmake: Optional[Dict[str, Any]] = field(default=None)
    stubgen: Optional[Dict[str, Any]] = field(default=None)
    cross: Optional[Dict[str, Any]] = field(default=None)


def read_metadata(pyproject_path, flag_overrides: Dict[str,
                                                       List[str]]) -> Config:
    # Load the pyproject.toml file
    pyproject_path = Path(pyproject_path)
    pyproject_folder = pyproject_path.parent
    pyproject = tomli.loads(pyproject_path.read_text('utf-8'))
    if 'project' not in pyproject:
        raise ConfigError('Missing [project] table')

    # Load local override
    localconfig_fname = 'py-build-cmake.local.toml'
    localconfig_path = pyproject_folder / localconfig_fname
    localconfig = None
    if localconfig_path.exists():
        localconfig = tomli.loads(localconfig_path.read_text('utf-8'))
        # treat empty local override as no local override
        localconfig = localconfig or None

    # Load override for cross-compilation
    crossconfig_fname = 'py-build-cmake.cross.toml'
    crossconfig_path = pyproject_folder / crossconfig_fname
    crossconfig = None
    if crossconfig_path.exists():
        crossconfig = tomli.loads(crossconfig_path.read_text('utf-8'))
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
        return tomli.loads(path.read_text('utf-8'))

    extra_flag_paths = {
        '--local': get_tool_pbc_path(),
        '--cross': get_cross_path(),
    }

    for flag, targetpath in extra_flag_paths.items():
        for path in flag_overrides[flag]:
            extra_options.append(
                OverrideConfigOption(
                    path,
                    "Command line override flag",
                    targetpath=targetpath,
                ))
            config_files[path] = try_load_local(Path(path))

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
    cfg.dynamic_metadata = flit_cfg.dynamic_metadata
    cfg.entrypoints = flit_cfg.entrypoints
    cfg.metadata = flit_cfg.metadata
    cfg.referenced_files = flit_cfg.referenced_files
    cfg.license = pyproject['project'].setdefault('license', {})

    opts = get_options(pyproject_path.parent)
    for o in extra_options:
        opts.insert(o)

    tree_config = ConfigNode.from_dict(config_files)
    opts.verify_all(tree_config)
    opts.override_all(tree_config)
    opts.inherit_all(tree_config)
    opts.update_default_all(tree_config)
    dictcfg = tree_config.to_dict()
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

    # Store the sdist folders (this is based on flit)
    def get_sdist_cludes(cfg):
        return {
            cl + '_patterns': _check_glob_patterns(cfg['sdist'][cl], cl)
            for cl in ('include', 'exclude')
        }

    cfg.sdist = {
        os: get_sdist_cludes(tool_cfg[os])
        for os in ("linux", "windows", "mac")
    }
    s = 'cross'
    if s in tool_cfg:
        cfg.sdist.update({
            'cross': get_sdist_cludes(tool_cfg[s]),
        })

    # Store the CMake configuration
    cfg.cmake = {
        os: tool_cfg[os]['cmake']
        for os in ("linux", "windows", "mac")
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
        f = 'copy_from_native_build'
        if f in cfg.cross:
            cfg.cross[f] = _check_glob_patterns(cfg.cross[f], f'cross.{f}')
        cfg.cmake.update({
            'cross': cfg.cross.pop('cmake', {}),
        })

    return cfg


def normalize_name_wheel(name):
    """https://www.python.org/dev/peps/pep-0427/#escaping-and-unicode"""
    return re.sub(r"[^\w\d.]+", "_", name, re.UNICODE)
