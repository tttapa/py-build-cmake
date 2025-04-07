from __future__ import annotations

import os
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ...common import ConfigError
from .config_path import ConfPath

if TYPE_CHECKING:
    from .config_reference import ConfigReference
from .value_reference import ValueReference


@dataclass
class DefaultValueWrapper:
    """To distinguish between None and DefaultValueWrapper(None)."""

    value: Any


class DefaultValue(ABC):
    @abstractmethod
    def get_default(
        self,
        defaulter: ConfigDefaulter,
    ) -> DefaultValueWrapper | None: ...

    @abstractmethod
    def get_name(self) -> str: ...


class ConfigDefaulter:
    def __init__(
        self,
        root: ConfigReference,
        root_values: ValueReference,
        ref: ConfigReference | None = None,
        value_path: ConfPath | None = None,
    ) -> None:
        if ref is None:
            ref = root
        if value_path is None:
            value_path = ConfPath()
        self.root = root
        self.root_values = root_values
        self.ref = ref
        self.value_path = value_path

    def get_value_or_default(self) -> DefaultValueWrapper | None:
        try:
            return DefaultValueWrapper(self.root_values.get_value(self.value_path))
        except KeyError:
            return self.ref.config.default.get_default(self)

    def update_default(self):
        value_set = True
        if not self.root_values.is_value_set(self.value_path):
            default = self.ref.config.default.get_default(self)
            if default is not None:
                default_value = ValueReference(self.value_path, default.value)
                default_value.values = self.ref.config.verify(default_value)
                value = self.ref.config.finalize(default_value)
                self.root_values.set_value(self.value_path, value)
            else:
                value_set = False
        if value_set:
            value_ref = self.root_values.sub_ref(self.value_path)
            for ref, value_path in self.ref.iter_sub_options(value_ref):
                ConfigDefaulter(
                    root=self.root,
                    root_values=self.root_values,
                    ref=ref.resolve_inheritance(self.root),
                    value_path=value_path,
                ).update_default()


class DefaultValueValue(DefaultValue):
    def __init__(self, value: Any) -> None:
        self.value = value

    def get_default(
        self,
        defaulter: ConfigDefaulter,
    ) -> DefaultValueWrapper | None:
        return DefaultValueWrapper(deepcopy(self.value))

    def get_name(self) -> str:
        if isinstance(self.value, bool):
            return str(self.value).lower()
        return repr(self.value)


class DefaultValueEnvVar(DefaultValue):
    def __init__(self, key: str, disable: bool) -> None:
        self.key = key
        self.disable = disable

    def get_default(
        self,
        defaulter: ConfigDefaulter,
    ) -> DefaultValueWrapper | None:
        if self.disable:
            return None
        value = os.getenv(self.key)
        if value is None:
            return None
        return DefaultValueWrapper(value)

    def get_name(self) -> str:
        return f"ENV{{{self.key}}}"


class NoDefaultValue(DefaultValue):
    def __init__(self, name: str = "none"):
        self.name = name

    def get_default(
        self,
        defaulter: ConfigDefaulter,
    ) -> DefaultValueWrapper | None:
        return None

    def get_name(self) -> str:
        return self.name


class MissingDefaultError(ConfigError):
    """The user did not provide a required value."""


class RequiredValue(DefaultValue):
    def get_default(
        self,
        defaulter: ConfigDefaulter,
    ) -> DefaultValueWrapper | None:
        msg = f"{defaulter.value_path} requires a value"
        raise MissingDefaultError(msg)

    def get_name(self) -> str:
        return "required"


class RefDefaultValue(DefaultValue):
    def __init__(self, path: ConfPath, relative: bool = False) -> None:
        super().__init__()
        self.path: ConfPath = path
        self.relative = relative

    def get_default(
        self,
        defaulter: ConfigDefaulter,
    ) -> DefaultValueWrapper | None:
        if self.relative:
            rel_path = ConfPath(("^", *self.path.pth))
            target_path = defaulter.ref.config_path.join(rel_path)
            value_path = defaulter.value_path.join(rel_path)
        else:
            value_path = target_path = self.path
        try:
            target_opt = defaulter.root.sub_ref(target_path)
        except KeyError as e:
            msg = f"DefaultValue: reference to nonexisting option {target_path}"
            msg += f" (in {defaulter.ref.config_path})"
            raise ValueError(msg) from e
        return ConfigDefaulter(
            root=defaulter.root,
            root_values=defaulter.root_values,
            ref=target_opt.resolve_inheritance(defaulter.root),
            value_path=value_path,
        ).get_value_or_default()

    def get_name(self) -> str:
        r = str(self.path)
        if not self.relative:
            r = "/" + r
        return r
