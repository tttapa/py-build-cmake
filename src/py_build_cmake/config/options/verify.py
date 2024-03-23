from __future__ import annotations

from copy import copy

from .config_reference import ConfigReference
from .value_reference import ValueReference


class ConfigVerifier:
    def __init__(
        self, root: ConfigReference, ref: ConfigReference, values: ValueReference
    ) -> None:
        self.root = root
        self.ref = ref
        self.values = values

    def verify(self):
        verified_values = ValueReference(
            self.values.value_path,
            self.ref.config.verify(copy(self.values)),
        )
        for name in self.ref.sub_options:
            if name in self.values.values:
                verified_values.values[name] = ConfigVerifier(
                    root=self.root,
                    ref=self.ref.sub_ref(name).resolve_inheritance(self.root),
                    values=verified_values.sub_ref(name),
                ).verify()
        return verified_values.values
