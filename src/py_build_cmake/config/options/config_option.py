from __future__ import annotations

from copy import copy, deepcopy
from difflib import get_close_matches
from typing import Any, Iterable

from ...common import ConfigError
from .config_path import ConfPath
from .default import DefaultValue, NoDefaultValue
from .value_reference import OverrideActionEnum, ValueReference

_MAGIC_CLEAR_VALUE = None


class ConfigOption:
    def __init__(
        self,
        name: str,
        description: str = "",
        example: str = "",
        default: DefaultValue | None = None,
        inherit_from: ConfPath | str | None = None,
        create_if_inheritance_target_exists: bool = False,
        sub_options: dict[str, ConfigOption] | None = None,
    ) -> None:
        if default is None:
            default = NoDefaultValue()
        if isinstance(inherit_from, str):
            inherit_from = ConfPath.from_string(inherit_from)
        if sub_options is None:
            sub_options = {}
        self.name = name
        self.description = description
        self.example = example
        self.sub_options: dict[str, ConfigOption] = sub_options
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

    def iter_sub_options(
        self, values: ValueReference
    ) -> Iterable[tuple[str, ConfPath]]:
        """Return the names of the sub-options of this config option, along with
        the corresponding value path relative to the given value pth."""
        for name in self.sub_options:
            yield name, values.value_path.join(name)

    def iter_set_sub_options(
        self, values: ValueReference
    ) -> Iterable[tuple[str, ValueReference]]:
        """Return the names of the sub-options of this config option, along with
        the corresponding value reference relative to the given value if set."""
        for name in self.sub_options:
            if values.is_value_set(name):
                yield name, values.sub_ref(name)

    def verify(self, values: ValueReference) -> Any:
        if values.action == OverrideActionEnum.Clear:
            return _MAGIC_CLEAR_VALUE
        if values.action not in (OverrideActionEnum.Assign, OverrideActionEnum.Default):
            msg = f"Option {values.value_path} does not support "
            msg += f"operation {values.action.value}"
            raise ConfigError(msg)
        if not isinstance(values.values, dict):
            msg = f"Type of {values.value_path} should be 'dict', "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)
        unknown_keys = set(values.values) - set(self.sub_options)
        msg = ""
        for k in sorted(unknown_keys):
            suggested = get_close_matches(k, self.sub_options, 3)
            msg = f"Unknown option '{k}' in {values.value_path}. "
            if suggested:
                msg += f"Did you mean: {', '.join(suggested)}\n"
        if msg:
            raise ConfigError(msg[:-1])
        return values.values

    def finalize(self, values: ValueReference) -> Any:
        if self.sub_options:
            for k in list(values.values):
                if values.values[k] == _MAGIC_CLEAR_VALUE:
                    del values.values[k]
        return values.values

    def override(self, old_value: ValueReference, new_value: ValueReference) -> Any:
        if new_value.values == _MAGIC_CLEAR_VALUE:
            return _MAGIC_CLEAR_VALUE
        return copy(old_value.values)


class MultiConfigOption(ConfigOption):
    def __init__(
        self,
        name: str,
        description: str = "",
        example: str = "",
        default: DefaultValue | None = None,
        inherit_from: ConfPath | str | None = None,
        create_if_inheritance_target_exists: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            example=example,
            default=default,
            inherit_from=inherit_from,
            create_if_inheritance_target_exists=create_if_inheritance_target_exists,
        )

    default_index = "*"

    def iter_sub_options(
        self, values: ValueReference
    ) -> Iterable[tuple[str, ConfPath]]:
        """Return the names of the sub-options of this config option, along with
        the corresponding value path relative to the given value pth."""
        if values.values is None:
            return
        for k in values.values:
            val = values.sub_ref(k)
            for name in self.sub_options:
                yield name, val.value_path.join(name)

    def iter_set_sub_options(
        self, values: ValueReference
    ) -> Iterable[tuple[str, ValueReference]]:
        """Return the names of the sub-options of this config option, along with
        the corresponding value reference relative to the given value if set."""
        if values.values is None:
            return
        for k in values.values:
            val = values.sub_ref(k)
            for name in self.sub_options:
                if val.is_value_set(name):
                    yield name, val.sub_ref(name)

    def _verify(self, values: ValueReference):
        if values.values is None:
            return
        assert self.default_index not in values.values
        unknown_keys = set(values.values) - set(self.sub_options)
        msg = ""
        for k in sorted(unknown_keys):
            suggested = get_close_matches(k, self.sub_options, 3)
            msg = f"Unknown option '{k}' in {values.value_path}. "
            if suggested:
                msg += f"Did you mean: {', '.join(suggested)}\n"
        if msg:
            raise ConfigError(msg[:-1])

    def _values_to_index_dict(self, values: ValueReference):
        vals: dict[str, dict | None] = {}
        for k in values.values:
            try:
                int(k)
            except ValueError:
                v0 = vals.setdefault(self.default_index, {})
                assert v0 is not None
                v0[k] = values.values[k]  # Copy any action as well
                continue
            vr = values.sub_ref(k)
            if vr.action == OverrideActionEnum.Clear:
                vals[k] = _MAGIC_CLEAR_VALUE
            elif vr.action not in (
                OverrideActionEnum.Assign,
                OverrideActionEnum.Default,
            ):
                msg = f"Option {vr.value_path} does not support "
                msg += f"operation {vr.action.value}"
                raise ConfigError(msg)
            else:
                vals[k] = vr.values  # Do not copy action
        return vals

    def verify(self, values: ValueReference) -> Any:
        if values.action == OverrideActionEnum.Clear:
            return _MAGIC_CLEAR_VALUE
        if values.action not in (OverrideActionEnum.Assign, OverrideActionEnum.Default):
            msg = f"Option {values.value_path} does not support "
            msg += f"operation {values.action.value}"
            raise ConfigError(msg)
        if not isinstance(values.values, dict):
            msg = f"Type of {values.value_path} should be 'dict', "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)
        if not all(isinstance(v, str) for v in values.values):
            msg = f"Type of keys in {values.value_path} should be 'str'"
            raise ConfigError(msg)
        vals = self._values_to_index_dict(values)
        for k, v in vals.items():
            self._verify(ValueReference(values.value_path.join(k), v))
        return vals

    def finalize(self, values: ValueReference) -> Any:
        from .config_reference import ConfigReference
        from .override import ConfigOverrider

        if values.is_value_set(self.default_index):
            # Our own option as a "single" ConfigOption
            opt = ConfigOption(
                name=self.name,
                description=self.description,
                example=self.example,
                default=self.default,
                inherit_from=self.inherits,
                create_if_inheritance_target_exists=self.create_if_inheritance_target_exists,
                sub_options=self.sub_options,
            )
            # Override the non-default items by the default item.
            ref = ConfigReference(ConfPath((self.name,)), opt)
            for k in list(values.values):
                if k == self.default_index:
                    continue
                if values.values[k] == _MAGIC_CLEAR_VALUE:
                    del values.values[k]
                    continue
                super_value = deepcopy(values.sub_ref(self.default_index))
                new_values = values.sub_ref(k)
                for name in self.sub_options:
                    if new_values.is_value_set(name):
                        if super_value.is_value_set(name):
                            new_value = ConfigOverrider(
                                root=None,
                                ref=ref.sub_ref(name),
                                values=super_value.sub_ref(name),
                                new_values=new_values.sub_ref(name),
                            ).override()
                        else:
                            new_value = new_values.sub_ref(name).values
                        super_value.set_value(name, new_value)
                values.set_value(k, super_value.values)
            if len(values.values) == 1:
                values.values["0"] = values.values.pop(self.default_index)
            else:
                values.clear_value(self.default_index)

        return values.values

    def override(self, old_value: ValueReference, new_value: ValueReference) -> Any:
        if new_value.values == _MAGIC_CLEAR_VALUE:
            return _MAGIC_CLEAR_VALUE
        # TODO: change implementation such that shallow copy is sufficient
        r = deepcopy(old_value.values) or {}
        for k, v in new_value.values.items():
            if v == _MAGIC_CLEAR_VALUE:
                r[k] = _MAGIC_CLEAR_VALUE
            else:
                r.setdefault(k, {})
        return r


class UncheckedConfigOption(ConfigOption):
    def verify(self, values: ValueReference):
        return values.values
