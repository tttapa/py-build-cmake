from __future__ import annotations

from copy import copy
from dataclasses import dataclass

from ...common import ConfigError
from .config_option import ConfigOption
from .config_path import ConfPath
from .default import DefaultValue
from .value_reference import OverrideActionEnum, ValueReference


@dataclass
class ListOption:
    value: list[str] | None = None
    append: list[str] | None = None
    prepend: list[str] | None = None
    remove: list[str] | None = None


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
        if old_value.values is None:
            old_value.values = ListOption(value=[])
        if new_value.values is None:
            return old_value.values
        a = copy(old_value.values)
        b = new_value.values
        assert isinstance(a, ListOption)
        assert isinstance(b, ListOption)
        self._combine_values_into(a, b)
        return a

    def _combine_values_into(self, a: ListOption, b: ListOption):  # noqa: PLR0912
        if b.value is not None:
            a.value = b.value
            a.remove = None
            a.prepend = None
            a.append = None
        elif a.value is None:
            if b.remove is not None:
                a.remove = b.remove
                if a.prepend is not None:
                    remove = set(b.remove)
                    a.prepend = [v for v in a.prepend if v not in remove]
                if a.append is not None:
                    remove = set(b.remove)
                    a.append = [v for v in a.append if v not in remove]
            if b.prepend is not None:
                a.prepend = b.prepend + (a.prepend or [])
            if b.append is not None:
                a.append = (a.append or []) + b.append
        else:
            if b.remove is not None:
                remove = set(b.remove)
                a.value = [v for v in a.value if v not in remove]
                # TODO: fix this and write comprehensive tests
                if a.prepend is not None:
                    remove = set(b.remove)
                    a.prepend = [v for v in a.prepend if v not in remove]
                if a.append is not None:
                    remove = set(b.remove)
                    a.append = [v for v in a.append if v not in remove]
            if b.append is not None:
                a.value = a.value + b.append
            if b.prepend is not None:
                a.value = b.prepend + a.value

    def _check_dict_keys(self, d: dict, pth):
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

    def verify(self, values: ValueReference):  # noqa: PLR0911
        v = values.values
        if isinstance(v, dict):
            return self._verify_dict(values)
        elif not isinstance(v, list):
            if self.convert_str_to_singleton and isinstance(v, str):
                v = [v]
            else:
                msg = f"Type of {values.value_path} should be {list}, "
                msg += f"not {type(v)}"
                raise ConfigError(msg)
        elif not all(isinstance(el, str) for el in v):
            msg = f"Type of elements in {values.value_path} should be {str}"
            raise ConfigError(msg)
        if values.action == OverrideActionEnum.Default:
            if self.append_by_default:
                return ListOption(append=v)
            return ListOption(value=v)
        elif values.action == OverrideActionEnum.Assign:
            return ListOption(value=v)
        elif values.action == OverrideActionEnum.Append:
            return ListOption(append=v)
        elif values.action == OverrideActionEnum.Prepend:
            return ListOption(prepend=v)
        elif values.action == OverrideActionEnum.Remove:
            return ListOption(remove=v)
        else:
            msg = f"Option {values.value_path} of type {self.get_typename()} "
            msg += f"does not support operation {values.action.value}"
            raise ConfigError(msg)

    def finalize(self, values: ValueReference):
        if isinstance(values.values, str):  # Could be because of default
            return [values.values]
        if isinstance(values.values, list):  # Could be because of default
            return values.values
        x = values.values
        y = ListOption(value=[])
        assert isinstance(x, ListOption)
        self._combine_values_into(y, x)
        assert y.value is not None
        return y.value
