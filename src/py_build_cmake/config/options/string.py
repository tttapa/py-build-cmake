from __future__ import annotations

from ...common import ConfigError
from .config_option import ConfigOption
from .value_reference import ValueReference


class StringConfigOption(ConfigOption):
    def get_typename(self, md: bool = False) -> str:
        return "string"

    def override(self, old_value, new_value):
        new, old = new_value.values, old_value.values
        if old is None:
            old = ""
        if new is None:
            return old
        assert isinstance(new, str)
        assert isinstance(old, str)
        return new_value.action.override_string(old, new)

    def verify(self, values: ValueReference):
        if self.sub_options:
            msg = f"Type of {values.value_path} should be {str}, "
            msg += f"not {dict}"
            raise ConfigError(msg)
        elif not isinstance(values.values, str):
            msg = f"Type of {values.value_path} should be {str}, "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)
        return values.values
