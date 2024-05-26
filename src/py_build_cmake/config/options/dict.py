from __future__ import annotations

from copy import deepcopy

from ...common import ConfigError
from .config_option import ConfigOption
from .value_reference import OverrideAction, OverrideActionEnum, ValueReference


class DictOfStrConfigOption(ConfigOption):
    def get_typename(self, md: bool = False) -> str:
        return "dict"

    def override(self, old_value: ValueReference, new_value: ValueReference):
        new, old = new_value.values, old_value.values
        if old is None:
            old = {}
        if new is None:
            return old
        r = {} if new_value.action == OverrideActionEnum.Assign else deepcopy(old)
        for k, v in new.items():
            if isinstance(v, str):
                r[k] = v
            else:
                assert isinstance(v, OverrideAction)
                assert isinstance(v.values, str)
                if v.action == OverrideActionEnum.Clear:
                    r.pop(k, None)
                else:
                    r[k] = v.action.override_string(r.get(k, ""), v.values)
        return r

    def verify(self, values: ValueReference):
        def validate_type(el):
            if isinstance(el, OverrideAction):
                return isinstance(el.values, str)
            return isinstance(el, str)

        if values.values is None:
            return None
        supported = (
            OverrideActionEnum.Assign,
            OverrideActionEnum.Default,
            OverrideActionEnum.Append,
        )
        if values.action not in supported:
            msg = f"Option {values.value_path} of type {self.get_typename()} "
            msg += f"does not support operation {values.action.value}"
            raise ConfigError(msg)
        valdict = values.values
        if not isinstance(valdict, dict):
            msg = f"Type of {values.value_path} should be {dict}, "
            msg += f"not {type(valdict)}"
            raise ConfigError(msg)
        elif not all(isinstance(el, str) for el in valdict):
            msg = f"Type of keys in {values.value_path} should be {str}"
            raise ConfigError(msg)
        elif not all(validate_type(el) for el in valdict.values()):
            msg = f"Type of values in {values.value_path} should be {str}"
            raise ConfigError(msg)
        return valdict
