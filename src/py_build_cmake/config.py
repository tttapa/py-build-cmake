from dataclasses import dataclass, field
import os
from pprint import pprint
import re
from typing import Any, Dict, List, Optional, Set
from pathlib import Path


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


def read_metadata(pyproject_path) -> Config:
    from flit_core.config import ConfigError
    import tomli

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

    return check_config(pyproject_path, pyproject,
                        (localconfig_fname, localconfig),
                        (crossconfig_fname, crossconfig))


def check_config(pyproject_path, pyproject, localcfg, crosscfg):
    from flit_core.config import read_pep621_metadata
    from flit_core.config import _check_glob_patterns

    # Check the package/module name and normalize it
    from distlib.util import normalize_name
    if (f := 'name') in pyproject['project']:
        normname = normalize_name(pyproject['project'][f])
        if pyproject['project'][f] != normname:
            raise RuntimeWarning(
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

    from .config_options import ConfigNode
    from .pyproject_options import get_options
    opts = get_options(pyproject_path.parent)

    localconfig_fname, localconfig = localcfg
    crossconfig_fname, crossconfig = crosscfg

    rawcfg = {
        "pyproject.toml": pyproject,
        localconfig_fname: localconfig,
        crossconfig_fname: crossconfig,
    }
    treecfg = ConfigNode.from_dict(rawcfg)
    opts.verify_all(treecfg)
    opts.override_all(treecfg)
    opts.inherit_all(treecfg)
    opts.update_default_all(treecfg)
    dictcfg = treecfg.to_dict()
    tool_cfg = dictcfg['pyproject.toml']['tool']['py-build-cmake']

    # Store the module configuration
    if (s := 'module') in tool_cfg:
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
    if (s := 'cross') in tool_cfg:
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
    if (s := 'stubgen') in tool_cfg:
        cfg.stubgen = tool_cfg[s]

    # Store the cross compilation configuration
    if (s := 'cross') in tool_cfg:
        cfg.cross = tool_cfg[s]
        if (f := 'copy_from_native_build') in cfg.cross:
            cfg.cross[f] = _check_glob_patterns(cfg.cross[f], f'cross.{f}')
        cfg.cmake.update({
            'cross': cfg.cross.pop('cmake', {}),
        })

    return cfg


def normalize_name_wheel(name):
    """https://www.python.org/dev/peps/pep-0427/#escaping-and-unicode"""
    return re.sub(r"[^\w\d.]+", "_", name, re.UNICODE)
