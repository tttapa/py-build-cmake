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
        for ref, val_ref in self.ref.iter_set_sub_options(final_values):
            final_val = ConfigFinalizer(
                root=self.root,
                ref=ref.resolve_inheritance(self.root),
                values=val_ref,
            ).finalize()
            rel = val_ref.value_path.relative_to(final_values.value_path)
            if final_val is None:
                final_values.clear_value(rel)
            else:
                final_values.set_value(rel, final_val)
        return final_values.values
