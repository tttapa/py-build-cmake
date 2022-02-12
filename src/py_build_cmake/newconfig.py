from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from functools import reduce
import os
from pathlib import Path
from pprint import pprint
from this import d
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

from flit_core.config import ConfigError

ConfPath = Tuple[str, ...]
ConfValue = Optional[Union[str, List[str], Dict[str, Any]]]
Conf = Dict[str, Any]


def pth(s: str) -> ConfPath:
    if not s:
        return ()
    return tuple(s.split('/'))


def pth2str(p: ConfPath) -> str:
    return '/'.join(p)


def joinpth(p1: ConfPath, p2: ConfPath) -> ConfPath:
    while p1 and p2 and p2[0] == '^':
        p1 = p1[:-1]
        p2 = p2[1:]
    return p1 + p2


def hasparent(path: ConfPath) -> bool:
    return len(path) >= 1


def parent(path: ConfPath) -> ConfPath:
    if not hasparent(path):
        raise RuntimeError(f"Path {pth2str(path)} does not have a parent")
    return path[:-1]


def basename(path: ConfPath) -> str:
    return path[-1]


class ConfigNode:

    def __init__(self,
                 value: ConfValue = None,
                 sub: Dict[str, 'ConfigNode'] = None) -> None:
        self.value: ConfValue = value
        self.sub: Optional[Dict[str, 'ConfigNode']] = sub

    @classmethod
    def from_dict(cls, d: dict):
        node = cls()
        node.sub = {}
        for k, v in d.items():
            if isinstance(v, dict):
                node.sub[k] = cls.from_dict(v)
            else:
                node.sub[k] = cls(value=v)
        return node

    def to_dict(self):
        if self.sub is None:
            return self.value
        return {k: v.to_dict() for k, v in self.sub.items()}

    def iter_dfs(self, path: ConfPath = ()):
        yield path, self.value
        if self.sub is not None:
            for name, sub in self.sub.items():
                for y in sub.iter_dfs(path + (name, )):
                    yield y

    def __getitem__(self, key):
        if isinstance(key, str):
            if self.sub is None:
                raise KeyError
            return self.sub[key]
        elif isinstance(key, tuple):
            if len(key) == 0:
                return self
            elif self.sub is None:
                raise KeyError
            else:
                return self.sub[key[0]][key[1:]]
        else:
            raise TypeError(key)

    def get(self, key: ConfPath, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, path: ConfPath, default: Any):
        tgt = self[parent(path)]
        if tgt.sub is None:
            tgt.sub = {}
        return tgt.sub.setdefault(basename(path), default)

    def contains(self, path: ConfPath):
        try:
            self[path]
            return True
        except KeyError:
            return False


@dataclass
class DefaultValueWrapper:
    value: ConfValue


class DefaultValue(ABC):

    @abstractmethod
    def get_default(self, rootopts: 'ConfigOption', opt: 'ConfigOption',
                    cfg: ConfigNode, cfgpath: ConfPath,
                    optpath: ConfPath) -> Optional[DefaultValueWrapper]:
        ...


class DefaultValueValue(DefaultValue):

    def __init__(self, value: ConfValue) -> None:
        self.value: ConfValue = value

    def get_default(self, rootopts: 'ConfigOption', opt: 'ConfigOption',
                    cfg: ConfigNode, cfgpath: ConfPath,
                    optpath: ConfPath) -> Optional[DefaultValueWrapper]:
        return DefaultValueWrapper(self.value)


class NoDefaultValue(DefaultValue):

    def get_default(self, rootopts: 'ConfigOption', opt: 'ConfigOption',
                    cfg: ConfigNode, cfgpath: ConfPath,
                    optpath: ConfPath) -> Optional[DefaultValueWrapper]:
        return None


class MissingDefaultError(ConfigError):
    pass


class RequiredValue(DefaultValue):

    def get_default(self, rootopts: 'ConfigOption', opt: 'ConfigOption',
                    cfg: ConfigNode, cfgpath: ConfPath,
                    optpath: ConfPath) -> Optional[DefaultValueWrapper]:
        raise MissingDefaultError(f'{pth2str(cfgpath)} requires a value')


class RefDefaultValue(DefaultValue):

    def __init__(self, path: ConfPath, relative: bool = False) -> None:
        super().__init__()
        self.path: ConfPath = path
        self.relative = relative

    def get_default(self, rootopts: 'ConfigOption', opt: 'ConfigOption',
                    cfg: ConfigNode, cfgpath: ConfPath,
                    optpath: ConfPath) -> Optional[DefaultValueWrapper]:
        abscfgpath = absoptpath = self.path
        if self.relative:
            absoptpath = joinpth(optpath, ('^', ) + absoptpath)
            abscfgpath = joinpth(cfgpath, ('^', ) + abscfgpath)
        opt = rootopts.get(absoptpath)
        if opt is None:
            raise ValueError("DefaultValue: reference to nonexisting option "
                             f"{pth2str(absoptpath)}")
        return opt.update_default(rootopts, cfg, abscfgpath, absoptpath)


class ConfigOption:

    allow_unknown_keys = False

    def __init__(self,
                 name: str,
                 description: str = '',
                 default: DefaultValue = NoDefaultValue(),
                 inherit_from: Optional[ConfPath] = None,
                 create_if_inheritance_target_exists: bool = False) -> None:
        self.name = name
        self.description = description
        self.sub: Dict[str, 'ConfigOption'] = {}
        self.default: DefaultValue = default
        self.inherit_from: Optional[ConfPath] = inherit_from
        self.create_if_inheritance_target_exists = create_if_inheritance_target_exists

    def insert(self, opt: 'ConfigOption'):
        assert opt.name not in self.sub
        self.sub[opt.name] = opt
        return self.sub[opt.name]

    def insert_multiple(self, opts: Iterable['ConfigOption']):
        for opt in opts:
            self.insert(opt)

    def iter_opt_paths(self) -> Iterator[ConfPath]:
        """DFS of the option tree."""
        for name, subopt in self.sub.items():
            yield (name, )
            for p in subopt.iter_opt_paths():
                yield (name, ) + p

    def iter_leaf_opt_paths(self) -> Iterator[ConfPath]:
        """DFS of the option tree."""
        if not self.sub:
            yield ()
        else:
            for name, subopt in self.sub.items():
                for p in subopt.iter_leaf_opt_paths():
                    yield (name, ) + p

    def iter_dfs(self, path: ConfPath = ()):
        yield path, self
        for name, sub in self.sub.items():
            for y in sub.iter_dfs(path + (name, )):
                yield y

    def __getitem__(self, key) -> 'ConfigOption':
        if isinstance(key, str):
            return self.sub[key]
        elif isinstance(key, tuple):
            if len(key) == 0:
                return self
            else:
                return self.sub[key[0]][key[1:]]
        else:
            raise TypeError(key)

    def get(self, key: ConfPath, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, path: ConfPath, default: Any):
        tgt = self[parent(path)]
        if tgt.sub is None:
            tgt.sub = {}
        return tgt.sub.setdefault(basename(path), default)

    def contains(self, path: ConfPath):
        try:
            self[path]
            return True
        except KeyError:
            return False

    def inherit(self, rootopts: 'ConfigOption', cfg: ConfigNode,
                selfpth: ConfPath):
        superpth = self.inherit_from
        if superpth is not None:
            # If the super option is not set, there's nothing to inherit
            if (supercfg := cfg.get(superpth)) is None:
                return

            # If this option is not set, but the super option is,
            # create our own config as well, including all of its parents,
            # but only if create_if_inheritance_target_exists is set on those
            # options
            selfcfg = self.create_parent_config_for_inheritance(
                rootopts, cfg, selfpth)
            if selfcfg is None:
                return

            # Find the option we inherit from and make sure it exists
            if (superopt := rootopts.get(superpth)) is None:
                raise ValueError(f'{pth2str(superpth)} is not a valid option')

            # Create a copy of the config of our super-option and override it
            # with our own config
            supercfg = deepcopy(supercfg)
            superopt.explicit_override(self, supercfg, superpth, selfcfg,
                                       selfpth)
            selfcfg.sub = supercfg.sub
        if self.sub:
            for name, sub in self.sub.items():
                sub.inherit(rootopts, cfg, selfpth + (name, ))

    @staticmethod
    def create_parent_config_for_inheritance(rootopts: 'ConfigOption',
                                             cfg: ConfigNode,
                                             selfpth: ConfPath):
        """
        Loop over all parent options of selfpth in rootopts and default-
        initialize their configuration in cfg to empty ConfigNodes if the 
        option's create_if_inheritance_target_exists is set to True.
        Returns cfg[selfpth] or None if parents were not created because of
        create_if_inheritance_target_exists.
        """
        selfcfg = None
        p: ConfPath = ()
        opt = rootopts
        create_paths: List[ConfPath] = []
        for s in selfpth:
            p += s,
            opt = opt[s]
            if (selfcfg := cfg.get(p)) is None:
                if not opt.create_if_inheritance_target_exists:
                    return None
                create_paths.append(p)
        for p in create_paths:
            selfcfg = cfg.setdefault(p, ConfigNode(sub={}))
        return selfcfg

    def explicit_override(self, rootopts: 'ConfigOption', selfcfg: ConfigNode,
                          selfpth: ConfPath, overridecfg: ConfigNode,
                          overridepath: ConfPath):
        # The default ConfigOption simply overrides all of its sub-options, but
        # this function is overridden by specific subclasses.
        if overridecfg.sub is None:
            return  # No sub-options, so nothing to override
        for name, subopt in self.sub.items():
            assert isinstance(selfcfg, ConfigNode)
            assert isinstance(overridecfg, ConfigNode)
            if name not in overridecfg.sub:
                continue
            subselfcfg = selfcfg.setdefault((name, ), ConfigNode())
            subpath = selfpth + (name, )
            suboverridepath = overridepath + (name, )
            suboverridecfg = overridecfg.sub[name]
            subopt.explicit_override(rootopts, subselfcfg, subpath,
                                     suboverridecfg, suboverridepath)
        if self.inherit_from is not None:
            superopt = rootopts[self.inherit_from]
            superopt.explicit_override(rootopts, selfcfg, selfpth, overridecfg,
                                       overridepath)

    def override(self, rootopts: 'ConfigOption', cfg: ConfigNode,
                 selfpath: ConfPath):
        """Override other options with this option if appropriate. This is a 
        no-op in most cases and only does something in OverrideConfigOption."""
        assert cfg.contains(selfpath)

    def verify_impl(self, rootopts: 'ConfigOption', cfg: ConfigNode,
                    cfgpath: ConfPath):
        assert cfg.contains(cfgpath)
        selfcfg = cfg[cfgpath]
        # Check if there are any unknown options in the config
        if not self.allow_unknown_keys:
            if (unkwn := set(selfcfg.sub or ()) - set(self.sub or ())):
                raise ConfigError(f'Unkown options in {pth2str(cfgpath)}: ' +
                                  ', '.join(unkwn))
        # Recursively verify the sub-options
        if selfcfg.sub:
            for name, sub in selfcfg.sub.items():
                if name in self.sub:
                    self.sub[name].verify(rootopts, cfg, cfgpath + (name, ))

    def verify(self, rootopts: 'ConfigOption', cfg: ConfigNode,
               cfgpath: ConfPath):
        if self.inherit_from is None:
            return self.verify_impl(rootopts, cfg, cfgpath)
        else:
            return rootopts[self.inherit_from].verify_impl(
                rootopts, cfg, cfgpath)

    def override_all(self, cfg: ConfigNode):
        # This is just me being lazy, we probably don't need to iterate over
        # all nodes ...
        for p, opt in self.iter_dfs():
            if cfg.contains(p):
                opt.override(self, cfg, p)

    def verify_all(self, cfg: ConfigNode):
        self.verify(self, cfg, ())

    def inherit_all(self, cfg: ConfigNode):
        self.inherit(self, cfg, ())

    def update_default(
            self,
            rootopts: 'ConfigOption',
            cfg: ConfigNode,
            cfgpath: ConfPath,
            selfpath: Optional[ConfPath] = None
    ) -> Optional[DefaultValueWrapper]:
        if selfpath is None:
            selfpath = cfgpath

        result = None
        # If the entire path exists in cfg, simply return that value
        if (cfgval := cfg.get(cfgpath)) is not None:
            result = cfgval
        # If the path is not yet in cfg
        else:
            assert self is rootopts[selfpath]
            # Find the default value for this option
            default = self.default.get_default(rootopts, self, cfg, cfgpath,
                                               selfpath)
            # If the parent is set in the config, set this value as well
            if default is not None and cfg.contains(parent(cfgpath)):
                cfgval = cfg.setdefault(cfgpath, ConfigNode())
                cfgval.value = default.value
            result = default

        if self.inherit_from is not None:
            targetopt = rootopts.get(self.inherit_from)
            if targetopt is None:
                raise ValueError(f"Inheritance {pth2str(selfpath)} targets "
                                 f"nonexisting option "
                                 f"{pth2str(self.inherit_from)}")
            for p, opt in targetopt.iter_dfs():
                if opt.inherit_from is not None:
                    # TODO: this might be too restrictive, but we need to break
                    # the recursion somehow ...
                    continue
                optpth = joinpth(self.inherit_from, p)
                newcfgpth = joinpth(cfgpath, p)
                opt.update_default(rootopts, cfg, newcfgpth, optpth)

        return result

    def update_default_all(self, cfg: ConfigNode):
        for p, opt in self.iter_dfs():
            if hasparent(p) and cfg.contains(parent(p)):
                opt.update_default(self, cfg, p)


class UncheckedConfigOption(ConfigOption):

    allow_unknown_keys = True


class StrConfigOption(ConfigOption):

    def explicit_override(self, opts: 'ConfigOption', selfcfg: ConfigNode,
                          selfpth: ConfPath, overridecfg: ConfigNode,
                          overridepath: ConfPath):
        assert not self.sub
        assert not selfcfg.sub
        assert not overridecfg.sub
        selfcfg.value = deepcopy(overridecfg.value)

    def verify(self, rootopts: 'ConfigOption', cfg: ConfigNode,
               cfgpath: ConfPath):
        if cfg[cfgpath].sub:
            raise ConfigError(f'Type of {pth2str(cfgpath)} should be '
                              f'{str}, not {dict}')
        elif not isinstance(cfg[cfgpath].value, str):
            raise ConfigError(f'Type of {pth2str(cfgpath)} should be '
                              f'{str}, not {type(cfg[cfgpath].value)}')


class PathConfigOption(StrConfigOption):

    def __init__(self,
                 name: str,
                 description: str,
                 default: DefaultValue = NoDefaultValue(),
                 must_exist: bool = True,
                 expected_contents: List[str] = [],
                 base_path: Optional[Path] = None):
        super().__init__(name, description, default)
        self.must_exist = must_exist
        self.expected_contents = expected_contents
        self.base_path = base_path

    def check_path(self, cfg: ConfigNode, cfgpath):
        path = cfg[cfgpath].value = os.path.normpath(cfg[cfgpath].value)
        if os.path.isabs(path):
            raise ConfigError(f'{pth2str(cfgpath)} must be a relative path')
        if self.base_path is not None:
            abspath = self.base_path / path
            if self.must_exist and not os.path.exists(abspath):
                raise ConfigError(f'{pth2str(cfgpath)}: {str(abspath)} '
                                  f'does not exist')
            missing = [
                sub for sub in self.expected_contents
                if not os.path.exists(os.path.join(abspath, sub))
            ]
            if missing:
                missingstr = '", "'.join(missing)
                raise ConfigError(f'{pth2str(cfgpath)} does not contain '
                                  f'required files or folders "{missingstr}"')

    def verify(self, rootopts: 'ConfigOption', cfg: ConfigNode,
               cfgpath: ConfPath):
        super().verify(rootopts, cfg, cfgpath)
        self.check_path(cfg, cfgpath)


class ListOfStrConfigOption(ConfigOption):

    def explicit_override(self, opts: 'ConfigOption', selfcfg: ConfigNode,
                          selfpth: ConfPath, overridecfg: ConfigNode,
                          overridepath: ConfPath):
        assert not self.sub
        assert not selfcfg.sub
        assert not overridecfg.sub
        if overridecfg.value is not None:
            if selfcfg.value is None:
                selfcfg.value = []
            assert isinstance(selfcfg.value, list)
            assert isinstance(overridecfg.value, list)
            selfcfg.value += deepcopy(overridecfg.value)

    def verify(self, rootopts: 'ConfigOption', cfg: ConfigNode,
               cfgpath: ConfPath):
        if cfg[cfgpath].sub:
            raise ConfigError(f'Type of {pth2str(cfgpath)} should be '
                              f'{list}, not {dict}')
        elif not isinstance(cfg[cfgpath].value, list):
            raise ConfigError(f'Type of {pth2str(cfgpath)} should be '
                              f'{list}, not {type(cfg[cfgpath].value)}')
        elif not all(isinstance(el, str) for el in cfg[cfgpath].value):
            raise ConfigError(f'Type of elements in {pth2str(cfgpath)} should '
                              f'be {str}')


class DictOfStrConfigOption(ConfigOption):

    def explicit_override(self, opts: 'ConfigOption', selfcfg: ConfigNode,
                          selfpth: ConfPath, overridecfg: ConfigNode,
                          overridepath: ConfPath):
        assert not self.sub
        assert not selfcfg.value
        assert not overridecfg.value
        if overridecfg.sub is not None:
            if selfcfg.sub is None:
                selfcfg.sub = {}
            assert isinstance(selfcfg.sub, dict)
            assert isinstance(overridecfg.sub, dict)
            selfcfg.sub |= deepcopy(overridecfg.sub)

    def verify(self, rootopts: 'ConfigOption', cfg: ConfigNode,
               cfgpath: ConfPath):
        valdict = cfg[cfgpath].sub
        if cfg[cfgpath].value:
            raise ConfigError(f'Type of {pth2str(cfgpath)} should be '
                              f'{dict}, not {type(cfg[cfgpath].value)}')
        elif not isinstance(valdict, dict):
            raise ConfigError(f'Type of {pth2str(cfgpath)} should be '
                              f'{dict}, not {type(valdict)}')
        elif not all(isinstance(el, str) for el in valdict.keys()):
            raise ConfigError(f'Type of keys in {pth2str(cfgpath)} should '
                              f'be {str}')
        elif not all(isinstance(el.value, str) for el in valdict.values()):
            raise ConfigError(f'Type of values in {pth2str(cfgpath)} should '
                              f'be {str}')


class OverrideConfigOption(ConfigOption):

    def __init__(
        self,
        name: str,
        description: str,
        targetpath: ConfPath,
        default: DefaultValue = NoDefaultValue()) -> None:
        super().__init__(name, description, default)
        self.targetpath = targetpath

    def verify(self, rootopts: 'ConfigOption', cfg: ConfigNode,
               cfgpath: ConfPath):
        rootopts[self.targetpath].verify(rootopts, cfg, cfgpath)

    def inherit(self, rootopts: 'ConfigOption', cfg: ConfigNode,
                selfpth: ConfPath):
        pass

    def override(self, rootopts: ConfigOption, cfg: ConfigNode,
                 cfgpath: ConfPath):
        if (selfcfg := cfg.get(cfgpath, None)) is None:
            return
        elif selfcfg.value is None and selfcfg.sub is None:
            return
        super().override(rootopts, cfg, cfgpath)
        curropt = rootopts[self.targetpath]
        self.create_parent_config(cfg, self.targetpath)
        currcfg = cfg[self.targetpath]
        overridecfg = cfg[cfgpath]
        # Override the config at those paths by our own config
        curropt.explicit_override(rootopts, currcfg, self.targetpath,
                                  overridecfg, cfgpath)

    @staticmethod
    def create_parent_config(cfg: ConfigNode, path: ConfPath):
        parentcfg = cfg
        for s in path:
            assert parentcfg.sub is not None
            parentcfg = parentcfg.sub.setdefault(s, ConfigNode(sub={}))


def get_options(config_path: Optional[Path] = None):
    root = ConfigOption("root")
    pyproject = root.insert(UncheckedConfigOption("pyproject.toml"))
    project = pyproject.insert(UncheckedConfigOption('project'))
    project.insert(UncheckedConfigOption('name', default=RequiredValue()))
    name_pth = pth('pyproject.toml/project/name')
    tool = pyproject.insert(UncheckedConfigOption("tool"))
    pbc = tool.insert(
        ConfigOption("py-build-cmake",
                     default=DefaultValueValue({}),
                     create_if_inheritance_target_exists=True))

    # [tool.py-build-cmake.module]
    module = pbc.insert(ConfigOption("module", default=DefaultValueValue({})))
    pbc_pth = pth('pyproject.toml/tool/py-build-cmake')
    module.insert_multiple([
        StrConfigOption('name',
                        "Import name in Python (can be different from the "
                        "name on PyPI, which is defined in the [project] "
                        "section).",
                        default=RefDefaultValue(name_pth)),
        PathConfigOption('directory',
                         "Directory containing the Python package.",
                         default=DefaultValueValue("."),
                         base_path=config_path),
    ])

    # [tool.py-build-cmake.sdist]
    sdist = pbc.insert(
        ConfigOption(
            "sdist",
            default=DefaultValueValue({}),
            create_if_inheritance_target_exists=True,
        ))
    sdist_pth = pth('pyproject.toml/tool/py-build-cmake/sdist')
    sdist.insert_multiple([
        ListOfStrConfigOption('include',
                              "Files and folders to include in the sdist "
                              "distribution. May include the '*' wildcard "
                              "(but not '**' for recursive patterns).",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption('exclude',
                              "Files and folders to exclude from the sdist "
                              "distribution. May include the '*' wildcard "
                              "(but not '**' for recursive patterns).",
                              default=DefaultValueValue([])),
    ])  # yapf: disable

    # [tool.py-build-cmake.cmake]
    cmake = pbc.insert(ConfigOption("cmake"))
    cmake_pth = pth('pyproject.toml/tool/py-build-cmake/cmake')
    cmake.insert_multiple([
        StrConfigOption('build_type',
                        "Build type passed to the configuration step, as "
                        "-DCMAKE_BUILD_TYPE=<?>.\n"
                        "For example: "
                        "build_type = \"RelWithDebInfo\""),
        StrConfigOption('config',
                        "Configuration type passed to the build and install "
                        "steps, as --config <?>.",
                        default=RefDefaultValue(pth('build_type'), relative=True)),
        StrConfigOption('generator',
                        "CMake generator to use, passed to the "
                        "configuration step, as "
                        "-G <?>."),
        PathConfigOption('source_path',
                         "Folder containing CMakeLists.txt.",
                         default=DefaultValueValue("."),
                         expected_contents=["CMakeLists.txt"],
                         base_path=config_path),
        PathConfigOption('build_path',
                         "CMake build and cache folder.",
                         default=DefaultValueValue('.py-build-cmake_cache'),
                         must_exist=False),
        DictOfStrConfigOption('options',
                              "Extra options passed to the configuration step, "
                              "as -D<option>=<value>.\n"
                              "For example: "
                              "options = {\"WITH_FEATURE_X\" = \"On\"}",
                              default=DefaultValueValue({})),
        ListOfStrConfigOption('args',
                              "Extra arguments passed to the configuration "
                              "step.\n"
                              "For example: "
                              "args = [\"--debug-find\", \"-Wdev\"]",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption('build_args',
                              "Extra arguments passed to the build step.\n"
                              "For example: "
                              "build_args = [\"-j\"]",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption('build_tool_args',
                              "Extra arguments passed to the build tool in the "
                              "build step (e.g. to Make or Ninja).\n"
                              "For example: "
                              "build_tool_args = [\"VERBOSE=1\"]",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption('install_args',
                              "Extra arguments passed to the install step.\n"
                              "For example: "
                              "install_args = [\"--strip\"]",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption("install_components",
                              "List of components to install, the install step "
                              "is executed once for each component, with the "
                              "option --component <?>.\n"
                              "Use an empty string to specify the default "
                              "component.",
                              default=DefaultValueValue([""])),
        DictOfStrConfigOption("env",
                              "Environment variables to set when running "
                              "CMake.",
                              default=DefaultValueValue({})),
    ])# yapf: disable

    # [tool.py-build-cmake.stubgen]
    stubgen = pbc.insert(ConfigOption("stubgen"))
    stubgen.insert_multiple([
        ListOfStrConfigOption('packages',
                              "List of packages to generate stubs for, passed "
                              "to stubgen as -p <?>."),
        ListOfStrConfigOption('modules',
                              "List of modules to generate stubs for, passed "
                              "to stubgen as -m <?>."),
        ListOfStrConfigOption('files',
                              "List of files to generate stubs for, passed to "
                              "stubgen without any flags."),
        ListOfStrConfigOption('args',
                              "List of extra arguments passed to stubgen.",
                              default=DefaultValueValue([])),
    ]) # yapf: disable

    # [tool.py-build-cmake.{linux,windows,mac}]
    for system in ["Linux", "Windows", "Mac"]:
        name = system.lower()
        opt = pbc.insert(
            ConfigOption(
                name,
                f"Override options for {system}.",
                create_if_inheritance_target_exists=True,
                default=DefaultValueValue({}),
            ))
        opt.insert_multiple([
            ConfigOption("sdist",
                         f"{system}-specific sdist options.",
                         inherit_from=sdist_pth,
                         create_if_inheritance_target_exists=True),
            ConfigOption("cmake",
                         f"{system}-specific CMake options.",
                         inherit_from=cmake_pth,
                         create_if_inheritance_target_exists=True),
        ])

    # [tool.py-build-cmake.cross]
    cross = pbc.insert(ConfigOption("cross"))
    cross_pth = pth('pyproject.toml/tool/py-build-cmake/cross')
    cross.insert_multiple([
        StrConfigOption('implementation',
                        "Identifier for the Python implementation.\n"
                        "For example: implementation = 'cp' # CPython",
                        default=RequiredValue()),
        StrConfigOption('version',
                        "Python version, major and minor, without dots.\n"
                        "For example: version = '310' # 3.10",
                        default=RequiredValue()),
        StrConfigOption('abi',
                        "Python ABI.\n"
                        "For example: abi = 'cp310'",
                        default=RequiredValue()),
        StrConfigOption('arch',
                        "Operating system and architecture (not dots or "
                        "dashes, only underscores, all lowercase).\n"
                        "For example: arch = 'linux_x86_64'",
                        default=RequiredValue()),
        PathConfigOption('toolchain_file',
                         "CMake toolchain file to use.",
                         default=RequiredValue(),
                         base_path=config_path),
        ListOfStrConfigOption('copy_from_native_build',
                              "If set, this will cause a native version of the "
                              "CMake project to be built and installed in a "
                              "temporary directory first, and the files in this "
                              "list will be copied to the final cross-compiled "
                              "package. This is useful if you need binary "
                              "utilities that run on the build system while "
                              "cross-compiling, or for things like stubs for "
                              "extension modules that cannot be generated while "
                              "cross-compiling.\n"
                              "May include the '*' wildcard "
                              "(but not '**' for recursive patterns)."),
        ConfigOption("sdist",
                     "Override sdist options when cross-compiling.",
                     inherit_from=sdist_pth),
        ConfigOption("cmake",
                     "Override CMake options when cross-compiling.",
                     inherit_from=cmake_pth),
    ]) # yapf: disable

    # local override
    root.insert(
        OverrideConfigOption("py-build-cmake.local.toml",
                             "Allows you to override the "
                             "settings in pyproject.toml",
                             targetpath=pbc_pth))

    # cross-compilation local override
    root.insert(
        OverrideConfigOption("py-build-cmake.cross.toml",
                             "Allows you to override the cross-"
                             "compilation settings in pyproject.toml",
                             targetpath=cross_pth))

    return root