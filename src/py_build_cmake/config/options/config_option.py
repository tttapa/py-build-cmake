from __future__ import annotations

from copy import copy
from difflib import get_close_matches
from typing import Any, Iterable

from ...common import ConfigError
from .config_path import ConfPath
from .default import DefaultValue, NoDefaultValue
from .value_reference import ValueReference


class ConfigOption:
    def __init__(
        self,
        name: str,
        description: str = "",
        example: str = "",
        default: DefaultValue | None = None,
        inherit_from: ConfPath | str | None = None,
        create_if_inheritance_target_exists: bool = False,
    ) -> None:
        if default is None:
            default = NoDefaultValue()
        if isinstance(inherit_from, str):
            inherit_from = ConfPath.from_string(inherit_from)
        self.name = name
        self.description = description
        self.example = example
        self.sub_options: dict[str, ConfigOption] = {}
        self.inherits = inherit_from
        self.default: DefaultValue = default
        self.create_if_inheritance_target_exists = create_if_inheritance_target_exists

    def insert(self, opt: ConfigOption):
        assert opt.name not in self.sub_options
        self.sub_options[opt.name] = opt
        return self.sub_options[opt.name]

    def insert_multiple(self, opts: Iterable[ConfigOption]):
        for opt in opts:
            self.insert(opt)
        return self

    def get_typename(self, md: bool = False) -> str | None:
        return None

    def verify(self, values: ValueReference) -> Any:
        if not isinstance(values.values, dict):
            msg = f"Type of {values.value_path} should be 'dict', "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)
        unknown_keys = set(values.values) - set(self.sub_options)
        msg = ""
        for k in sorted(unknown_keys):
            suggested = get_close_matches(k, self.sub_options, 3)
            msg = f"Unknown option '{k}' in {values.value_path}. "
            msg += f"Did you mean: {', '.join(suggested)}\n"
        if msg:
            raise ConfigError(msg[:-1])
        return values.values

    def finalize(self, values: ValueReference) -> Any:
        return values.values

    def override(self, old_value: ValueReference, new_value: ValueReference) -> Any:
        return copy(old_value.values)


class UncheckedConfigOption(ConfigOption):
    def verify(self, values: ValueReference):
        return values.values
