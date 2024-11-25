from __future__ import annotations

from copy import copy

from ...common import ConfigError
from .config_reference import ConfigReference
from .value_reference import OverrideActionEnum, ValueReference


class ConfigVerifier:
    def __init__(
        self, root: ConfigReference, ref: ConfigReference, values: ValueReference
    ) -> None:
        self.root = root
        self.ref = ref
        self.values = values

    def verify(self):
        # If this option should be cleared, it shouldn't have a value
        if (
            self.values.action == OverrideActionEnum.Clear
            and self.values.values is not None
        ):
            msg = f'Operation "clear" ({self.values.action.value}) '
            msg += f"cannot have a value in {self.values.value_path}"
            raise ConfigError(msg)
        # Verify our own option
        verified_values = ValueReference(
            self.values.value_path,
            self.ref.config.verify(copy(self.values)),
            self.values.action,
        )
        # Verify our sub-options
        for ref, sub_val in self.ref.iter_set_sub_options(verified_values):
            verified = ConfigVerifier(
                root=self.root,
                ref=ref.resolve_inheritance(self.root),
                values=sub_val,
            ).verify()
            rel = sub_val.value_path.relative_to(verified_values.value_path)
            verified_values.set_value(rel, verified)
        return verified_values.values
