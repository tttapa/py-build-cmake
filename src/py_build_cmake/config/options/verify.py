from __future__ import annotations

from copy import copy

from ...common import ConfigError
from .config_reference import ConfigReference
from .value_reference import OverrideAction, OverrideActionEnum, ValueReference


class ConfigVerifier:
    def __init__(
        self, root: ConfigReference, ref: ConfigReference, values: ValueReference
    ) -> None:
        self.root = root
        self.ref = ref
        self.values = values

    def verify(self):
        # If this option should be cleared, there's nothing to verify
        if self.values.action == OverrideActionEnum.Clear:
            if self.values.values is not None:
                msg = f'Operation "clear" ({self.values.action.value}) '
                msg += f"cannot have a value in {self.values.value_path}"
                raise ConfigError(msg)
            verified_values = self.values
        else:
            # Verify our own option
            verified_values = ValueReference(
                self.values.value_path,
                self.ref.config.verify(copy(self.values)),
                self.values.action,
            )
            # Verify our sub-options
            for name in self.ref.sub_options:
                if name in self.values.values:
                    sub_val = verified_values.sub_ref(name)
                    verified = ConfigVerifier(
                        root=self.root,
                        ref=self.ref.sub_ref(name).resolve_inheritance(self.root),
                        values=sub_val,
                    ).verify()
                    verified_values.values[name] = verified
        # Preserve the override actions
        if verified_values.action == OverrideActionEnum.Default:
            return verified_values.values
        else:
            return OverrideAction(
                values=verified_values.values, action=verified_values.action
            )
