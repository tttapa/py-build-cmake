from __future__ import annotations

from ...common import ConfigError
from .config_option import ConfigOption
from .config_path import ConfPath
from .default import DefaultValue, NoDefaultValue
from .value_reference import OverrideActionEnum, ValueReference


class EnumConfigOption(ConfigOption):
    def __init__(
        self,
        name: str,
        description: str = "",
        example: str = "",
        default: DefaultValue | None = None,
        inherit_from: ConfPath | str | None = None,
        create_if_inheritance_target_exists: bool = False,
        options: list[str] | None = None,
    ) -> None:
        if default is None:
            default = NoDefaultValue()
        if options is None:
            options = []
        super().__init__(
            name,
            description,
            example,
            default,
            inherit_from,
            create_if_inheritance_target_exists,
        )
        self.options = options

    def get_typename(self, md: bool = False):
        if md:
            return "`'" + "'` \\| `'".join(self.options) + "'`"
        else:
            return "'" + "' | '".join(self.options) + "'"

    def override(self, old_value: ValueReference, new_value: ValueReference):
        return new_value.values

    def verify(self, values: ValueReference):
        if values.values is None:
            return None
        if values.action not in (OverrideActionEnum.Assign, OverrideActionEnum.Default):
            msg = f"Enumeration option {values.value_path} "
            msg += f"does not support operation {values.action.value}"
            raise ConfigError(msg)
        elif not isinstance(values.values, str):
            msg = f"Type of {values.value_path} should be {str}, "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)
        if values.values not in self.options:
            msg = f"Value of {values.value_path} should be one of "
            msg += "'" + "', '".join(self.options) + "'"
            raise ConfigError(msg)
        return values.values
