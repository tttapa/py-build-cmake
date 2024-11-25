from __future__ import annotations

from copy import copy
from dataclasses import dataclass

from ...common import ConfigError
from .config_option import ConfigOption
from .config_path import ConfPath
from .default import DefaultValue
from .string import StringOption
from .value_reference import OverrideActionEnum, ValueReference


@dataclass
class ListOption:
    clear: bool = False
    value: list[str] | None = None
    append: list[str] | None = None
    prepend: list[str] | None = None
    remove: list[str] | None = None

    @classmethod
    def from_values(cls, values: ValueReference, append_by_default: bool):
        val = values.values
        if values.action == OverrideActionEnum.Clear:
            assert val is None
            return cls(clear=True)
        if not isinstance(val, list) or not all(isinstance(v, str) for v in val):
            msg = f"Invalid type {type(val)}"
            raise AssertionError(msg)
        if values.action == OverrideActionEnum.Default:
            return cls(append=val) if append_by_default else cls(value=val)
        if values.action == OverrideActionEnum.Assign:
            return cls(value=val)
        if values.action == OverrideActionEnum.Remove:
            return cls(remove=val)
        if values.action == OverrideActionEnum.Append:
            return cls(append=val)
        if values.action == OverrideActionEnum.Prepend:
            return cls(prepend=val)
        msg = f"Invalid action {values.action}"
        raise AssertionError(msg)

    def override(self, new: ListOption):
        # Clearing always propagates
        if new.clear:
            return copy(new)
        old = copy(self)
        # If we're overriding with a value, the old value is not used
        if new.value is not None:
            old.value = new.value
            old.append = new.append
            old.prepend = new.prepend
            old.remove = []
            return old
        # Otherwise, we're simply appending to or removing from the old value,
        # and these changes are propagated down to the old value.
        if new.remove is not None:
            old.remove = (old.remove or []) + new.remove
            if old.value:
                old.value = [e for e in old.value if e not in new.remove]
            if old.prepend:
                old.prepend = [e for e in old.prepend if e not in new.remove]
            if old.append:
                old.append = [e for e in old.append if e not in new.remove]
        if new.append is not None:
            old.append = (old.append or []) + new.append
        if new.prepend is not None:
            old.prepend = new.prepend + (old.prepend or [])
        return old

    def finalize(self) -> list[str] | None:
        empty = True
        final = []
        if self.value is not None:
            empty = False
            final = self.value
        if self.append is not None:
            empty = False
            final = final + self.append
        if self.prepend is not None:
            empty = False
            final = self.prepend + final
        return None if (empty and self.clear) else final


class ListOfStrConfigOption(ConfigOption):
    def __init__(
        self,
        name: str,
        description: str = "",
        example: str = "",
        default: DefaultValue | None = None,
        inherit_from: ConfPath | str | None = None,
        create_if_inheritance_target_exists: bool = False,
        convert_str_to_singleton=False,
        append_by_default=False,
    ) -> None:
        super().__init__(
            name,
            description,
            example,
            default,
            inherit_from,
            create_if_inheritance_target_exists,
        )
        self.convert_str_to_singleton = convert_str_to_singleton
        self.append_by_default = append_by_default

    valid_keys = frozenset(("+", "-", "=", "append", "remove", "value", "prepend"))

    def get_typename(self, md: bool = False):
        return "list+" if self.append_by_default else "list"

    def override(self, old_value: ValueReference, new_value: ValueReference):
        new, old = new_value.values, copy(old_value.values)
        if old is None:  # No previous value
            old = ListOption()
        assert isinstance(new, ListOption)
        assert isinstance(old, ListOption)
        return old.override(new)

    def _check_dict_keys(self, d: dict, pth: ConfPath):
        invalid_keys = set(d) - self.valid_keys
        if invalid_keys:
            msg = f"Invalid keys in {pth}: {list(invalid_keys)}"
            raise ConfigError(msg)
        if "value" in d and "=" in d:
            msg = f"Invalid keys in {pth}: "
            msg += 'Cannot combine "value" and "="'
            raise ConfigError(msg)
        if "append" in d and "+" in d:
            msg = f"Invalid keys in {pth}: "
            msg += 'Cannot combine "append" and "+"'
            raise ConfigError(msg)
        if "remove" in d and "-" in d:
            msg = f"Invalid keys in {pth}: "
            msg += 'Cannot combine "remove" and "-"'
            raise ConfigError(msg)
        if "value" in d or "=" in d:
            invalid_keys = {"+", "append", "-", "remove", "prepend"} & set(d)
            if invalid_keys:
                msg = f"Invalid keys in {pth}: "
                msg += 'Cannot combine "value" or "=" with the '
                msg += f"following keys: {list(invalid_keys)}"
                raise ConfigError(msg)

    def _verify_dict(self, values: ValueReference) -> ListOption:
        if values.action not in (OverrideActionEnum.Assign, OverrideActionEnum.Default):
            msg = f"Type of {values.value_path} should be {list}, "
            msg += f"not {dict}"
            raise ConfigError(msg)
        x = values.values
        self._check_dict_keys(x, values.value_path)
        opt = ListOption()
        if "=" in x:
            x["value"] = x.pop("=")
        if "+" in x:
            x["append"] = x.pop("+")
        if "-" in x:
            x["remove"] = x.pop("-")
        for k in ("value", "append", "remove", "prepend"):
            if k not in x:
                continue
            v = x.pop(k)
            pthname = f"{values.value_path}[{k}]"
            if not isinstance(v, list):
                msg = f"Type of {pthname} should be {list}, not {type(v)}"
                raise ConfigError(msg)
            if not all(isinstance(el, str) for el in v):
                msg = f"Type of elements in {pthname} should be {str}"
                raise ConfigError(msg)
            setattr(opt, k, v)
        assert not x
        return opt

    def verify(self, values: ValueReference):
        if isinstance(values.values, dict):
            return self._verify_dict(values)
        elif not isinstance(values.values, list):
            if self.convert_str_to_singleton and isinstance(values.values, str):
                values.values = values.values = [values.values]
            elif values.values is None and values.action == OverrideActionEnum.Clear:
                pass
            else:
                msg = f"Type of {values.value_path} should be {list}, "
                msg += f"not {type(values.values)}"
                raise ConfigError(msg)
        elif not all(isinstance(el, str) for el in values.values):
            msg = f"Type of elements in {values.value_path} should be {str}"
            raise ConfigError(msg)
        path_actions = (OverrideActionEnum.AppendPath, OverrideActionEnum.PrependPath)
        if values.action in path_actions:
            msg = f"Option {values.value_path} of type {self.get_typename()} "
            msg += f"does not support operation {values.action.value}"
            raise ConfigError(msg)
        return ListOption.from_values(values, self.append_by_default)

    def finalize(self, values: ValueReference):
        val = values.values
        if isinstance(val, list):
            return val
        # We allow lists inheriting from strings
        if self.convert_str_to_singleton and isinstance(val, StringOption):
            val = val.finalize()
            return None if val is None else [val]
        # The following is the main case
        assert isinstance(val, ListOption)
        return val.finalize()
