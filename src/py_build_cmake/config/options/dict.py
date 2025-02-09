from __future__ import annotations

from copy import deepcopy

from ...common import ConfigError
from .config_option import ConfigOption
from .string import StringOption
from .value_reference import OverrideActionEnum, ValueReference


class DictOfStrConfigOption(ConfigOption):
    def __init__(self, *args, finalize_to_str: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.finalize_to_str = finalize_to_str

    def get_typename(self, md: bool = False) -> str:
        return "dict"

    def override(self, old_value: ValueReference, new_value: ValueReference):
        if new_value.values is None:
            return None
        if old_value.values is None:
            old_value.values = {}
        r = deepcopy(old_value.values)
        for k, v in new_value.values.items():
            if k not in r:
                r[k] = deepcopy(v)
            else:
                r[k] = r[k].override(v)
        return r

    def _verify_str(self, values: ValueReference):
        if not isinstance(values.values, str):
            msg = f"Type of values in {values.value_path} should be str, "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)

    def verify(self, values: ValueReference):
        if values.values is None:
            return None
        if values.action not in (OverrideActionEnum.Append, OverrideActionEnum.Default):
            msg = f"Option {values.value_path} of type {self.get_typename()} "
            msg += f"does not support operation {values.action.value}"
            raise ConfigError(msg)

        if not isinstance(values.values, dict):
            msg = f"Type of {values.value_path} should be {dict}, "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)
        elif not all(isinstance(el, str) for el in values.values):
            msg = f"Type of keys in {values.value_path} should be {str}"
            raise ConfigError(msg)
        for k in values.values:
            self._verify_str(values.sub_ref(k))

        valdict: dict[str, StringOption] = {}
        for k in values.values:
            valdict[k] = StringOption.from_values(values.sub_ref(k))
        return valdict

    def finalize(self, values: ValueReference) -> dict[str, str] | None:
        if not self.finalize_to_str:
            return values.values
        if values.values is None:
            return None
        options: dict[str, str] = {}
        for k, v in values.values.items():
            if v is not None:
                assert isinstance(v, StringOption)
                str_v = v.finalize()
                if str_v is not None:
                    options[k] = str_v
        return options
