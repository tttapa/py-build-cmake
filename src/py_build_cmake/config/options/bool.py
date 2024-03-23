from ...common import ConfigError
from .config_option import ConfigOption
from .value_reference import ValueReference


class BoolConfigOption(ConfigOption):
    def get_typename(self, md: bool = False):
        return "bool"

    def override(self, old_value, new_value):
        if new_value.values is None:
            return old_value.values
        return new_value.values

    def verify(self, values: ValueReference):
        if self.sub_options:
            msg = f"Type of {values.value_path} should be {bool}, "
            msg += f"not {dict}"
            raise ConfigError(msg)
        elif not isinstance(values.values, bool):
            msg = f"Type of {values.value_path} should be {bool}, "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)
        return values.values
