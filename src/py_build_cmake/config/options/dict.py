from __future__ import annotations

from copy import deepcopy

from ...common import ConfigError
from .config_option import ConfigOption
from .value_reference import ValueReference


class DictOfStrConfigOption(ConfigOption):
    def get_typename(self, md: bool = False) -> str:
        return "dict"

    def override(self, old_value: ValueReference, new_value: ValueReference):
        if old_value.values is None:
            old_value.values = {}
        if new_value.values is None:
            return old_value.values
        r = deepcopy(old_value.values)
        r.update(deepcopy(new_value.values))
        return r

    def verify(self, values: ValueReference):
        if values.values is None:
            return None
        valdict = values.values
        if not isinstance(valdict, dict):
            msg = f"Type of {values.value_path} should be {dict}, "
            msg += f"not {type(valdict)}"
            raise ConfigError(msg)
        elif not all(isinstance(el, str) for el in valdict):
            msg = f"Type of keys in {values.value_path} should be {str}"
            raise ConfigError(msg)
        elif not all(isinstance(el, str) for el in valdict.values()):
            msg = f"Type of values in {values.value_path} should be {str}"
            raise ConfigError(msg)
        return valdict
