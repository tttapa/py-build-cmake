from ...common import ConfigError
from .config_option import ConfigOption
from .value_reference import OverrideActionEnum, ValueReference


class BoolConfigOption(ConfigOption):
    def get_typename(self, md: bool = False):
        return "bool"

    def override(self, old_value, new_value):
        return new_value.values

    def verify(self, values: ValueReference):
        if values.values is None:
            return None
        if values.action not in (OverrideActionEnum.Assign, OverrideActionEnum.Default):
            msg = f"Option {values.value_path} of type {self.get_typename()} "
            msg += f"does not support operation {values.action.value}"
            raise ConfigError(msg)
        elif not isinstance(values.values, bool):
            msg = f"Type of {values.value_path} should be {bool}, "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)
        return values.values
