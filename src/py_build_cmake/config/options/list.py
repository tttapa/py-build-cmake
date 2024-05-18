from __future__ import annotations

from copy import copy

from ...common import ConfigError
from .config_option import ConfigOption
from .config_path import ConfPath
from .default import DefaultValue
from .value_reference import ValueReference


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

    list_op_keys = frozenset(("+", "-", "=", "value", "append", "prepend"))

    def get_typename(self, md: bool = False):
        return "list+" if self.append_by_default else "list"

    def _override_list(self, old_value: ValueReference, new_value: ValueReference):
        assert isinstance(new_value.values, list)
        if self.append_by_default:
            assert isinstance(old_value.values, list)
            return copy(old_value.values + new_value.values)
        else:
            return copy(new_value.values)

    def _override_dict(self, old_value: ValueReference, new_value: ValueReference):
        assert isinstance(new_value.values, dict)
        if "=" in new_value.values:
            return copy(new_value.values["="])
        if "value" in new_value.values:
            return copy(new_value.values["value"])
        result = copy(old_value.values)
        if "-" in new_value.values:
            remove = set(new_value.values["-"])
            result = [v for v in result if v not in remove]
        if "+" in new_value.values:
            result = result + new_value.values["+"]
        if "append" in new_value.values:
            result = result + new_value.values["append"]
        if "prepend" in new_value.values:
            result = new_value.values["prepend"] + result
        return result

    def override(self, old_value: ValueReference, new_value: ValueReference):
        if old_value.values is None:
            old_value.values = []
        if new_value.values is None:
            return old_value.values
        if not isinstance(old_value.values, list):
            msg = f"Type of {old_value.value_path} should be {list}, "
            msg += f"not {type(old_value.values)}"
            raise ConfigError(msg)
        if isinstance(new_value.values, dict):
            return self._override_dict(old_value, new_value)
        return self._override_list(old_value, new_value)

    def verify(self, values: ValueReference):
        if isinstance(values.values, dict):
            invalid_keys = set(values.values.keys()) - self.list_op_keys
            if invalid_keys:
                inv_str = ", ".join(map(str, invalid_keys))
                val_str = ", ".join(map(str, self.list_op_keys))
                msg = f"Invalid keys in {values.value_path}: {inv_str} "
                msg += f"(valid keys are: {val_str})"
                raise ConfigError(msg)
            for k, v in values.values.items():
                pthname = f"{values.value_path}[{k}]"
                if not isinstance(v, list):
                    msg = f"Type of {pthname} should be {list}, not {type(v)}"
                    raise ConfigError(msg)
                if not all(isinstance(el, str) for el in v):
                    msg = f"Type of elements in {pthname} should be {str}"
                    raise ConfigError(msg)
        elif not isinstance(values.values, list):
            if self.convert_str_to_singleton and isinstance(values.values, str):
                values.values = [values.values]
            else:
                msg = f"Type of {values.value_path} should be {list}, "
                msg += f"not {type(values.values)}"
                raise ConfigError(msg)
        elif not all(isinstance(el, str) for el in values.values):
            msg = f"Type of elements in {values.value_path} should be {str}"
            raise ConfigError(msg)
        return values.values

    def finalize(self, values: ValueReference):
        if isinstance(values.values, str):
            return [values.values]
        return values.values
