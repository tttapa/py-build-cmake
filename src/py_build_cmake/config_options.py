"""
Classes to define hierarchical configuration options which support inheriting
from other options, default values, overriding options, etc.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
import os
from pathlib import Path
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
                raise KeyError()
            return self.sub[key]
        elif isinstance(key, tuple):
            if len(key) == 0:
                return self
            elif self.sub is None:
                raise KeyError()
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

    @abstractmethod
    def get_name(self) -> str:
        ...


class DefaultValueValue(DefaultValue):

    def __init__(self, value: ConfValue) -> None:
        self.value: ConfValue = value

    def get_default(self, rootopts: 'ConfigOption', opt: 'ConfigOption',
                    cfg: ConfigNode, cfgpath: ConfPath,
                    optpath: ConfPath) -> Optional[DefaultValueWrapper]:
        return DefaultValueWrapper(self.value)

    def get_name(self):
        return repr(self.value)


class NoDefaultValue(DefaultValue):

    def get_default(self, rootopts: 'ConfigOption', opt: 'ConfigOption',
                    cfg: ConfigNode, cfgpath: ConfPath,
                    optpath: ConfPath) -> Optional[DefaultValueWrapper]:
        return None

    def get_name(self):
        return 'none'


class MissingDefaultError(ConfigError):
    pass


class RequiredValue(DefaultValue):

    def get_default(self, rootopts: 'ConfigOption', opt: 'ConfigOption',
                    cfg: ConfigNode, cfgpath: ConfPath,
                    optpath: ConfPath) -> Optional[DefaultValueWrapper]:
        raise MissingDefaultError(f'{pth2str(cfgpath)} requires a value')

    def get_name(self):
        return 'required'


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

    def get_name(self) -> str:
        r = pth2str(self.path).replace('^', '..')
        if not self.relative:
            r = '/' + r
        return r


class ConfigOption:

    allow_unknown_keys = False

    def __init__(self,
                 name: str,
                 description: str = '',
                 example: str = '',
                 default: DefaultValue = NoDefaultValue(),
                 inherit_from: Optional[ConfPath] = None,
                 create_if_inheritance_target_exists: bool = False) -> None:
        self.name = name
        self.description = description
        self.example = example
        self.sub: Dict[str, 'ConfigOption'] = {}
        self.default: DefaultValue = default
        self.inherit_from: Optional[ConfPath] = inherit_from
        self.create_if_inheritance_target_exists = create_if_inheritance_target_exists

    def get_typename(self):
        return None

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
            supercfg = cfg.get(superpth)
            if supercfg is None:
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
            superopt = rootopts.get(superpth)
            if superopt is None:
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
            selfcfg = cfg.get(p)
            if selfcfg is None:
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
            unknwn = set(selfcfg.sub or ()) - set(self.sub or ())
            if unknwn:
                raise ConfigError(f'Unkown options in {pth2str(cfgpath)}: ' +
                                  ', '.join(unknwn))
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
        cfgval = cfg.get(cfgpath)
        if cfgval is not None:
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
                if cfgval.value is not None:
                    self.verify(rootopts, cfg, cfgpath)
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

    def get_typename(self):
        return 'string'

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
                 description: str = '',
                 example: str = '',
                 default: DefaultValue = NoDefaultValue(),
                 must_exist: bool = True,
                 expected_contents: List[str] = [],
                 base_path: Optional[Path] = None):
        super().__init__(name, description, example, default)
        self.must_exist = must_exist
        self.expected_contents = expected_contents
        self.base_path = base_path

    def get_typename(self):
        return 'path'

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

    def __init__(self,
                 name: str,
                 description: str = '',
                 example: str = '',
                 default: DefaultValue = NoDefaultValue(),
                 inherit_from: Optional[ConfPath] = None,
                 create_if_inheritance_target_exists: bool = False,
                 convert_str_to_singleton=False) -> None:
        super().__init__(name, description, example, default, inherit_from,
                         create_if_inheritance_target_exists)
        self.convert_str_to_singleton = convert_str_to_singleton

    def get_typename(self):
        return 'list'

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
            if self.convert_str_to_singleton and \
                    isinstance(cfg[cfgpath].value, str):
                cfg[cfgpath].value = [cfg[cfgpath].value]
            else:
                raise ConfigError(f'Type of {pth2str(cfgpath)} should be '
                                  f'{list}, not {type(cfg[cfgpath].value)}')
        elif not all(isinstance(el, str) for el in cfg[cfgpath].value):
            raise ConfigError(f'Type of elements in {pth2str(cfgpath)} should '
                              f'be {str}')


class DictOfStrConfigOption(ConfigOption):

    def get_typename(self):
        return 'dict'

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
            selfcfg.sub.update(deepcopy(overridecfg.sub))

    def verify(self, rootopts: 'ConfigOption', cfg: ConfigNode,
               cfgpath: ConfPath):
        if cfg[cfgpath].value is not None:
            if isinstance(cfg[cfgpath].value, dict):
                newcfg = ConfigNode.from_dict(cfg[cfgpath].value)
                cfg[cfgpath].value = newcfg.value
                cfg[cfgpath].sub = newcfg.sub
            else:
                raise ConfigError(f'Type of {pth2str(cfgpath)} should be '
                                  f'{dict}, not {type(cfg[cfgpath].value)}')
        valdict = cfg[cfgpath].sub
        if not isinstance(valdict, dict):
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
        super().__init__(name, description, '', default)
        self.targetpath = targetpath

    def verify(self, rootopts: 'ConfigOption', cfg: ConfigNode,
               cfgpath: ConfPath):
        rootopts[self.targetpath].verify(rootopts, cfg, cfgpath)

    def inherit(self, rootopts: 'ConfigOption', cfg: ConfigNode,
                selfpth: ConfPath):
        pass

    def override(self, rootopts: ConfigOption, cfg: ConfigNode,
                 cfgpath: ConfPath):
        selfcfg = cfg.get(cfgpath, None)
        if selfcfg is None:
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
