from copy import deepcopy
from dataclasses import dataclass, field
from functools import reduce
import os
import platform
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type, Union
from pathlib import Path

from abc import ABC, abstractmethod

NormPrefix_t = Tuple[str, ...]
Prefix_t = Union[NormPrefix_t, str]


class ConfigOption(ABC):

    class _Tag:
        pass

    Required = _Tag()
    NoDefault = _Tag()

    def __init__(self,
                 prefix: Prefix_t,
                 name: str,
                 helpstring: str,
                 default: Any = NoDefault):
        self.prefix = self.normalize_prefix(prefix)
        self.name = name
        self.helpstring = helpstring
        self.default = default

    @staticmethod
    def normalize_prefix(prefix: Prefix_t) -> NormPrefix_t:
        if isinstance(prefix, str):
            prefix = tuple(prefix.split('.'))
        return prefix

    @staticmethod
    def stringify_prefix(prefix: Prefix_t) -> str:
        if isinstance(prefix, str):
            return prefix

        def quote(component):
            return f'"{component}"' if '.' in component else component

        return '.'.join(map(quote, prefix))

    @abstractmethod
    def verify(self, config: dict):
        """Verify that this option in config is valid (correct type, path
        exists, etc."""
        ...

    @abstractmethod
    def get_typename(self) -> str:
        """Get the type of this option. Used when printing the help message."""
        ...

    def help(self):
        print(self.name)
        print(self.helpstring)

    @property
    def fullname(self):
        return '.'.join(self.prefix) + '.' + self.name

    def check_type(self, config: dict, cls: Type):
        """Check that this option in config has the given type."""
        from flit_core.config import ConfigError
        if not isinstance(config[self.name], cls):
            raise ConfigError(
                f"Type of field {self.fullname} should be {cls}, "
                f"not {type(config[self.name])}")

    def override(self, config: dict, overrideconfig: dict):
        """Override this option in config by this option in overrideconfig."""
        self.verify(overrideconfig)
        config[self.name] = overrideconfig[self.name]


class UncheckedOption(ConfigOption):

    def verify(self, config: dict):
        pass

    def get_typename(self) -> str:
        return super().get_typename()


class ConfigOptionRef:

    def __init__(self, prefix: Prefix_t):
        self.prefix = ConfigOption.normalize_prefix(prefix)


class ConfigOptions:

    def __init__(self):
        self.options: Dict[str, Any] = {}

    def add_options(self, options: Iterable[ConfigOption]):
        for option in options:
            self.add_option(option)

    def add_option(self, option: ConfigOption):
        self._add_option(option.prefix, option.name, option)

    def _add_option(self, prefix: NormPrefix_t, name: str,
                    value: ConfigOption):
        d = self.options
        for key in prefix:
            d = d.setdefault(key, {})
        d[name] = value

    def get_option(self, prefix, name=None):
        return self.get_option_prefix(prefix, name)[0]

    @staticmethod
    def index_with_prefix(data: Dict, prefix: Iterable):
        return reduce(lambda d, k: d[k], prefix, data)

    @staticmethod
    def index_with_prefix_default(data: Dict, prefix: Iterable, default=None):
        try:
            return reduce(lambda d, k: d[k], prefix, data)
        except KeyError:
            return default

    def get_option_prefix(self, prefix, name=None):
        prefix = ConfigOption.normalize_prefix(prefix)
        if name is not None:
            prefix = prefix + (name, )
        d = self.index_with_prefix(self.options, prefix)
        return d, prefix

    def _update_value(self, fullcfg: Dict, opt: ConfigOption,
                      cfgs: Optional[Dict], name: str):
        """
        If `cfg` is not None, return `cfg[name]`.
        If `config[name]` is not set, replace it by the default for this option.
        If the default option that is referred to is not set, this function 
        calls itself recursively to get the default value for that option.
        Raises `ConfigError` when a required option is not present.
        """
        from flit_core.config import ConfigError
        if cfgs is None or name not in cfgs:
            if opt.default is ConfigOption.Required:
                raise ConfigError(f"Missing required option {opt.fullname}")
            if isinstance(opt.default, ConfigOptionRef):
                subprefix = opt.default.prefix[:-1]
                subname = opt.default.prefix[-1]
                subopt = self.index_with_prefix(self.options,
                                                opt.default.prefix)
                subcfg = self.index_with_prefix_default(
                    fullcfg, subprefix, None)
                default = self._update_value(fullcfg, subopt, subcfg, subname)
                if cfgs is not None:
                    cfgs[name] = deepcopy(default)
                return default
            if opt.default is not ConfigOption.NoDefault:
                if cfgs is not None:
                    cfgs[name] = deepcopy(opt.default)
                return opt.default
        else:
            return cfgs[name]

    def update_defaults(self, cfg: Dict, prefix=()):
        prefix = ConfigOption.normalize_prefix(prefix)
        opts = self.index_with_prefix(self.options, prefix)
        cfgs = self.index_with_prefix(cfg, prefix)
        for name, opt in opts.items():
            if isinstance(opt, dict):
                if name in cfgs:
                    self.update_defaults(cfg, prefix + (name, ))
            else:
                self._update_value(cfg, opt, cfgs, name)

    def verify(self, cfg: Dict, prefix=()):
        prefix = ConfigOption.normalize_prefix(prefix)
        opts = self.index_with_prefix(self.options, prefix)
        cfgs = self.index_with_prefix(cfg, prefix)
        for name, opt in opts.items():
            if isinstance(opt, dict):
                if name in cfgs:
                    self.verify(cfg, prefix + (name, ))
            elif name in cfgs:
                opt.verify(cfgs)

    def override(self, cfg: Dict, prefix, overridecfg: Dict):
        prefix = ConfigOption.normalize_prefix(prefix)
        opts = self.index_with_prefix(self.options, prefix)
        cfgs = self.index_with_prefix(cfg, prefix)
        for name, opt in opts.items():
            if isinstance(opt, dict):
                if name in overridecfg:
                    cfgs.setdefault(name, {})
                    self.override(cfg, prefix + (name, ), overridecfg[name])
            elif name in overridecfg:
                opt.override(cfgs, overridecfg)

    def check_unknown_sections(self, cfg: Dict, prefix):
        """
        Raise a ConfigError if ``d`` contains any keys not in ``known_sections``.
        Keys starting with ``x-`` are ignored.
        """
        prefix_str = ConfigOption.stringify_prefix(prefix)
        prefix = ConfigOption.normalize_prefix(prefix)
        opts = self.index_with_prefix(self.options, prefix)
        cfgs = self.index_with_prefix(cfg, prefix)

        ignored = lambda s: s.lower().startswith('x-')
        unknown_sections = {s for s in set(cfgs) - set(opts) if not ignored(s)}
        if unknown_sections:
            from flit_core.config import ConfigError
            raise ConfigError('Unexpected tables or keys in pyproject.toml: ' +
                              ', '.join('[{}.{}]'.format(prefix_str, s)
                                        for s in unknown_sections))

        for name, opt in opts.items():
            if isinstance(opt, dict):
                if name in cfgs:
                    self.check_unknown_sections(cfg, prefix + (name, ))


class StringConfigOption(ConfigOption):

    def verify(self, config: dict):
        self.check_type(config, str)

    def get_typename(self) -> str:
        return "string"


class PathConfigOption(StringConfigOption):

    def __init__(self,
                 prefix: Prefix_t,
                 name: str,
                 helpstring: str,
                 default: Any = None,
                 must_exist: bool = True,
                 expected_contents: List[str] = []):
        super().__init__(prefix, name, helpstring, default)
        self.must_exist = must_exist
        self.expected_contents = expected_contents

    def check_path(self, config: dict):
        from flit_core.config import ConfigError
        path = config[self.name] = os.path.normpath(config[self.name])
        if os.path.isabs(path):
            raise ConfigError(f'{self.fullname} must be a relative path')
        if self.must_exist and not os.path.exists(path):
            raise ConfigError(f'{self.fullname} does not exist')
        for sub in self.expected_contents:
            if not os.path.exists(os.path.join(path, sub)):
                raise ConfigError(f'{self.fullname} does not contain required '
                                  f'file or folder "{sub}"')

    def verify(self, config: dict):
        super().verify(config)
        self.check_path(config)

    def get_typename(self) -> str:
        return "path"


class DictOfStringOption(ConfigOption):

    def verify(self, config: dict):
        if not isinstance(config[self.name], dict) or \
        not all(isinstance(k, str) and isinstance(v, str)
            for k, v in config[self.name].items()):
            from flit_core.config import ConfigError
            raise ConfigError(
                f"Type of {self.fullname} should be dict of strings to strings"
            )

    def override(self, config: dict, overrideconfig: dict):
        self.verify(overrideconfig)
        config[self.name].update(overrideconfig[self.name])

    def get_typename(self) -> str:
        return "dict"


class OverrideSectionConfigOption(ConfigOption):

    def verify(self, config: dict):
        if not isinstance(config[self.name], dict):
            from flit_core.config import ConfigError
            raise ConfigError(f"The field {self.fullname} should be a section")

    def get_typename(self) -> str:
        return "section"


class ListOfStringOption(ConfigOption):

    def verify(self, config: dict):
        if not isinstance(config[self.name], list) or \
        not all(isinstance(v, str) and isinstance(v, str)
            for v in config[self.name]):
            from flit_core.config import ConfigError
            raise ConfigError(
                f"Type of {self.fullname} should be list of strings")

    def override(self, config: dict, overrideconfig: dict):
        self.verify(overrideconfig)
        config[self.name] += overrideconfig[self.name]

    def get_typename(self) -> str:
        return "list"


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


def read_metadata(pyproject_path) -> Config:
    from flit_core.config import read_pep621_metadata, ConfigError
    from flit_core.config import _check_glob_patterns
    from flit_core.config import _check_type, _check_list_of_str
    import tomli

    # Load the pyproject.toml file
    pyproject_path = Path(pyproject_path)
    pyproject_folder = pyproject_path.parent
    pyproject = tomli.loads(pyproject_path.read_text('utf-8'))
    if 'project' not in pyproject:
        raise ConfigError('Missing [project] table')

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
    cfg.license = pyproject['project'].get('license', {})

    # Parse the tool-specific sections [tool.py-build-cmake.xxx]
    tool_name = 'py-build-cmake'
    tool_prefix_str = f'tool.{tool_name}'
    tool_opts = get_config_options(tool_prefix_str)

    # Check that the config doesn't contain any unknown sections or keys,
    # set options to their defaults if not specified, and verify their types,
    # make sure that file paths exist and are relative, etc.
    tool_cfg = pyproject.setdefault('tool', {
        tool_name: {}
    }).setdefault(tool_name, {})
    tool_cfg.setdefault('module', {})
    tool_opts.check_unknown_sections(pyproject, tool_prefix_str)
    tool_opts.update_defaults(pyproject, tool_prefix_str)
    tool_opts.verify(pyproject, tool_prefix_str)

    # Parse module configuration
    if (s := 'module') in tool_cfg:
        normname = normalize_name_wheel(tool_cfg[s]['name'])
        if tool_cfg[s]['name'] != normname:
            print(f"Name changed from {tool_cfg[s]['name']} to {normname}")
        tool_cfg[s]['name'] = normname
        cfg.module = tool_cfg[s]
    else:
        assert False, "Missing [tools.py-build-cmake.module] section"

    # Parse the sdist folders (this is based on flit)
    if (s := 'sdist') in tool_cfg:
        cfg.sdist['include_patterns'] = _check_glob_patterns(
            tool_cfg[s].get('include', []), 'include')
        cfg.sdist['exclude_patterns'] = _check_glob_patterns(
            tool_cfg[s].get('exclude', []), 'exclude')

    # Parse the CMake configuration
    if (s := 'cmake') in tool_cfg:
        systemname = {
            "Linux": "linux",
            "Windows": "windows",
            "Darwin": "mac",  # TODO: untested
        }[platform.system()]
        if systemname in tool_cfg[s]:
            tool_opts.override(pyproject, tool_prefix_str + '.cmake',
                               tool_cfg[s][systemname])
        cfg.cmake = tool_cfg[s]

    # Parse stubgen configuration
    if (s := 'stubgen') in tool_cfg:
        cfg.stubgen = tool_cfg[s]

    return cfg


def get_config_options(tool_prefix_str):
    tool_opts = ConfigOptions()

    mod_prefix_str = tool_prefix_str + '.module'
    tool_opts.add_options([
        UncheckedOption('project', 'name', ""),
        StringConfigOption(mod_prefix_str, 'name',
                           "Import name in Python (can be different from the "
                           "name on PyPI, which is defined in the [project] "
                           "section).",
                           default=ConfigOptionRef('project.name')),
        PathConfigOption(mod_prefix_str, 'directory',
                         "Directory containing the Python package.",
                         default="."),
    ]) # yapf: disable

    sdist_prefix_str = tool_prefix_str + '.sdist'
    tool_opts.add_options([
        ListOfStringOption(sdist_prefix_str, 'include',
                           "Files and folders to include in the sdist "
                           "distribution. May include the '*' wildcard "
                           "(but not '**' for recursive patterns).",
                           default=[]),
        ListOfStringOption(sdist_prefix_str, 'exclude',
                           "Files and folders to exclude from the sdist "
                           "distribution. May include the '*' wildcard "
                           "(but not '**' for recursive patterns).",
                           default=[]),
    ]) # yapf: disable

    cmake_prefix_str = tool_prefix_str + '.cmake'
    tool_opts.add_options([
        StringConfigOption(cmake_prefix_str, 'build_type',
                           "Build type passed to the configuration step, as "
                           "-DCMAKE_BUILD_TYPE=<?>.\n"
                           "For example: "
                           "build_type = \"RelWithDebInfo\""),
        StringConfigOption(cmake_prefix_str, 'config',
                           "Configuration type passed to the build and install "
                           "steps, as --config <?>.",
                           default=ConfigOptionRef(
                               cmake_prefix_str + '.build_type')),
        StringConfigOption(cmake_prefix_str, 'generator',
                           "CMake generator to use, passed to the "
                           "configuration step, as "
                           "-G <?>."),
        PathConfigOption(cmake_prefix_str, 'source_path',
                           "Folder containing CMakeLists.txt.",
                           default=".",
                           expected_contents=["CMakeLists.txt"]),
        PathConfigOption(cmake_prefix_str, 'build_path',
                           "CMake build and cache folder.",
                           default='.py-build-cmake_cache',
                           must_exist=False),
        DictOfStringOption(cmake_prefix_str, 'options',
                           "Extra options passed to the configuration step, "
                           "as -D<option>=<value>.\n"
                           "For example: "
                           "options = {\"WITH_FEATURE_X\" = \"On\"}",
                           default={}),
        ListOfStringOption(cmake_prefix_str, 'args',
                           "Extra arguments passed to the configuration step.\n"
                           "For example: "
                           "args = [\"--debug-find\", \"-Wdev\"]",
                           default=[]),
        ListOfStringOption(cmake_prefix_str, 'build_args',
                           "Extra arguments passed to the build step.\n"
                           "For example: "
                           "build_args = [\"-j\"]",
                           default=[]),
        ListOfStringOption(cmake_prefix_str, 'build_tool_args',
                           "Extra arguments passed to the build tool in the "
                           "build step (e.g. to Make or Ninja).\n"
                           "For example: "
                           "build_tool_args = [\"VERBOSE=1\"]",
                           default=[]),
        ListOfStringOption(cmake_prefix_str, 'install_args',
                           "Extra arguments passed to the install step.\n"
                           "For example: "
                           "install_args = [\"--strip\"]",
                           default=[]),
        ListOfStringOption(cmake_prefix_str, "install_components",
                           "List of components to install, the install step "
                           "is executed once for each component, with the "
                           "option --component <?>.\n"
                           "Use an empty string to specify the default "
                           "component.",
                           default=[""]),
        DictOfStringOption(cmake_prefix_str, "env",
                           "Environment variables to set when running CMake.",
                           default={}),
        OverrideSectionConfigOption(cmake_prefix_str, "linux",
                                    "Override options for Linux."),
        OverrideSectionConfigOption(cmake_prefix_str, "windows",
                                    "Override options for Windows."),
        OverrideSectionConfigOption(cmake_prefix_str, "mac",
                                    "Override options for Mac."),
    ]) # yapf: disable

    stubgen_prefix_str = tool_prefix_str + '.stubgen'
    tool_opts.add_options([
        ListOfStringOption(stubgen_prefix_str,
                           'packages',
                           "List of packages to generate stubs for, passed to "
                           "stubgen as -p <?>.",
                           default=[]),
        ListOfStringOption(stubgen_prefix_str,
                           'modules',
                           "List of modules to generate stubs for, passed to "
                           "stubgen as -m <?>.",
                           default=[]),
        ListOfStringOption(stubgen_prefix_str,
                           'files',
                           "List of files to generate stubs for, passed to "
                           "stubgen without any flags.",
                           default=[]),
        ListOfStringOption(stubgen_prefix_str,
                           'args',
                           "List of extra arguments passed to stubgen.",
                           default=[]),
    ])
    # yapf: disable
    return tool_opts


def normalize_name_wheel(name):
    """https://www.python.org/dev/peps/pep-0427/#escaping-and-unicode"""
    return re.sub("[^\w\d.]+", "_", name, re.UNICODE)
