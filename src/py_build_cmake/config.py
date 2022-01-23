from dataclasses import dataclass, field, fields
import os
from typing import Any, Dict, List, Optional, Set

from pathlib import Path


@dataclass
class Config:
    dynamic_metadata: Set[str] = field(default_factory=set)
    entrypoints: Dict[str, Dict[str, str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    referenced_files: List[str] = field(default_factory=list)
    sdist: Dict[str, List[str]] = field(default_factory=dict)
    license: Dict[str, str] = field(default_factory=dict)
    cmake: Optional[Dict[str, Any]] = field(default=None)
    stubgen: Optional[Dict[str, Any]] = field(default=None)


def read_metadata(path) -> Config:
    from flit_core.config import read_pep621_metadata, ConfigError
    from flit_core.config import _check_glob_patterns
    from flit_core.config import _check_type, _check_list_of_str
    import tomli

    # Load the pyproject.toml file
    path = Path(path)
    pyproject = tomli.loads(path.read_text('utf-8'))
    # Parse the [project] section for metadata (using flit's parser)
    if 'project' not in pyproject:
        raise ConfigError('Missing [project] table')
    flit_cfg = read_pep621_metadata(pyproject['project'], path)
    # Create our own config data structure using flit's output
    cfg = Config()
    cfg.dynamic_metadata = flit_cfg.dynamic_metadata
    cfg.entrypoints = flit_cfg.entrypoints
    cfg.metadata = flit_cfg.metadata
    cfg.referenced_files = flit_cfg.referenced_files
    cfg.license = pyproject['project'].get('license', {})

    from distlib.util import normalize_name
    if (f := 'name') in cfg.metadata:
        cfg.metadata[f] = normalize_name(cfg.metadata[f])

    # Parse the tool-specific sections [tool.py-build-cmake.xxx]
    tool_name = 'py-build-cmake'
    tool_prefix = f'tool.{tool_name}'
    dtool = pyproject.get('tool', {}).get(tool_name, {})
    known_sections = {'sdist', 'cmake', 'stubgen'}
    check_unknown_sections(tool_prefix, dtool, known_sections)

    # Parse the sdist folders (this is based on flit as well)
    if (s := 'sdist') in dtool:
        known_keys = {'include', 'exclude'}
        check_unknown_sections(f'{tool_prefix}.{s}', dtool[s], known_keys)

        cfg.sdist['include_patterns'] = _check_glob_patterns(
            dtool[s].get('include', []), 'include')
        cfg.sdist['exclude_patterns'] = _check_glob_patterns(
            dtool[s].get('exclude', []), 'exclude')
    assert s in known_sections

    # Parse the CMake configuration
    if (s := 'cmake') in dtool:
        known_keys = {
            'build_type', 'config', 'generator', 'source_path', 'build_path',
            'options', 'args', 'build_args', 'build_tool_args', 'install_args',
            'install_components', 'install_extra_components', 'env'
        }
        check_unknown_sections(f'{tool_prefix}.{s}', dtool[s], known_keys)
        cfg.cmake = dtool[s]
        assert cfg.cmake is not None

        if (f := 'build_type') in cfg.cmake:
            _check_type(cfg.cmake, f, str)
        assert f in known_keys
        if (f := 'config') in cfg.cmake:
            _check_type(cfg.cmake, f, str)
        assert f in known_keys
        if (f := 'generator') in cfg.cmake:
            _check_type(cfg.cmake, f, str)
        assert f in known_keys
        if (f := 'source_path') in cfg.cmake:
            check_path(cfg, f, 'CMake source_path')
        assert f in known_keys
        if (f := 'build_path') in cfg.cmake:
            check_path(cfg, f, 'CMake build_path')
        assert f in known_keys
        if (f := 'options') in cfg.cmake:
            _check_dict_of_str(cfg.cmake, f)
        assert f in known_keys
        if (f := 'args') in cfg.cmake:
            _check_list_of_str(cfg.cmake, f)
        assert f in known_keys
        if (f := 'build_args') in cfg.cmake:
            _check_list_of_str(cfg.cmake, f)
        assert f in known_keys
        if (f := 'build_tool_args') in cfg.cmake:
            _check_list_of_str(cfg.cmake, f)
        assert f in known_keys
        if (f := 'install_args') in cfg.cmake:
            _check_list_of_str(cfg.cmake, f)
        assert f in known_keys
        if (f := 'install_components') in cfg.cmake:
            _check_list_of_str(cfg.cmake, f)
            if 'install_extra_components' in cfg.cmake:
                raise ConfigError("Only one of install_components and "
                                  "install_extra_components can be present")
        assert f in known_keys
        if (f := 'install_extra_components') in cfg.cmake:
            _check_list_of_str(cfg.cmake, f)
        assert f in known_keys
        if (f := 'env') in cfg.cmake:
            _check_dict_of_str(cfg.cmake, f)
        assert f in known_keys
    assert s in known_sections

    # Parse the mypy stubgen configuration
    if (s := 'stubgen') in dtool:
        known_keys = {'packages', 'modules', 'files', 'args'}
        check_unknown_sections(f'{tool_prefix}.{s}', dtool[s], known_keys)
        cfg.stubgen = dtool[s]
        assert cfg.stubgen is not None

        if (f := 'packages') in cfg.stubgen:
            _check_list_of_str(cfg.stubgen, f)
        assert f in known_keys
        if (f := 'modules') in cfg.stubgen:
            _check_list_of_str(cfg.stubgen, f)
        assert f in known_keys
        if (f := 'files') in cfg.stubgen:
            _check_list_of_str(cfg.stubgen, f)
        assert f in known_keys
        if (f := 'args') in cfg.stubgen:
            _check_list_of_str(cfg.stubgen, f)
        assert f in known_keys
    assert s in known_sections

    return cfg


def check_path(cfg, f, msg):
    from flit_core.config import ConfigError
    from flit_core.config import _check_type
    _check_type(cfg.cmake, f, str)
    cfg.cmake[f] = os.path.normpath(cfg.cmake[f])
    if os.path.isabs(cfg.cmake[f]):
        raise ConfigError(f'{msg} must be relative')
    if not os.path.exists(cfg.cmake[f]):
        raise ConfigError(f'{msg} does not exist')


def check_unknown_sections(sec_prefix, d, known_sections):
    """
    Raise a ConfigError if ``d`` contains any keys not in ``known_sections``.
    Keys starting with ``x-`` are ignored.
    """
    ignored = lambda s: s.lower().startswith('x-')
    unknown_sections = {s for s in set(d) - known_sections if not ignored(s)}
    if unknown_sections:
        from flit_core.config import ConfigError
        raise ConfigError('Unexpected tables or keys in pyproject.toml: ' +
                          ', '.join('[{}.{}]'.format(sec_prefix, s)
                                    for s in unknown_sections))


def _check_dict_of_str(d, field_name):
    """
    Raise a ConfigError if ``d[field_name]`` is not of type ``Dict[str,str]``.
    """
    if not isinstance(d[field_name], dict) or \
        not all(isinstance(k, str) and isinstance(v, str)
                for k, v in d[field_name].items()):
        from flit_core.config import ConfigError
        raise ConfigError(
            "{} field should be a dict of strings to strings".format(
                field_name))
