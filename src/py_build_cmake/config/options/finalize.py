from __future__ import annotations

from copy import copy

from .config_reference import ConfigReference
from .value_reference import ValueReference


class ConfigFinalizer:
    def __init__(
        self, root: ConfigReference, ref: ConfigReference, values: ValueReference
    ) -> None:
        self.root = root
        self.ref = ref
        self.values = values

    def finalize(self):
        final_values = ValueReference(
            self.values.value_path,
            self.ref.config.finalize(copy(self.values)),
        )
        for name in self.ref.sub_options:
            if name in final_values.values:
                final_values.values[name] = ConfigFinalizer(
                    root=self.root,
                    ref=self.ref.sub_ref(name).resolve_inheritance(self.root),
                    values=final_values.sub_ref(name),
                ).finalize()
        return final_values.values
