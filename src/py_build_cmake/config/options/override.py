from __future__ import annotations

from typing import Any

from .config_path import ConfPath
from .config_reference import ConfigReference
from .value_reference import ValueReference


class ConfigOverrider:
    def __init__(
        self,
        root: ConfigReference | None,
        ref: ConfigReference,
        values: ValueReference,
        new_values: ValueReference,
    ) -> None:
        self.ref = ref
        self.root = root
        self.values = values
        self.new_values = new_values

    def override(self):
        # Override our own value
        overridden_values = ValueReference(
            self.values.value_path,
            self.ref.config.override(self.values, self.new_values),
        )
        # If we have sub-options, override those
        for ref, new_val in self.ref.iter_set_sub_options(self.new_values):
            if self.root is not None:
                ref = ref.resolve_inheritance(self.root)  # noqa: PLW2901
            rel = new_val.value_path.relative_to(self.new_values.value_path)
            # Create default parent options if necessary (for MultiConfigOption)
            if not self._create_default_parents(overridden_values, ref, rel):
                continue
            # Replace the old value by the override
            old_val = overridden_values.sub_ref(rel)
            overridden_values.set_value(
                rel,
                ConfigOverrider(
                    root=self.root,
                    ref=ref,
                    values=old_val,
                    new_values=new_val,
                ).override(),
            )
        return overridden_values.values

    def _create_default_parents(
        self, overridden_values: ValueReference, ref: ConfigReference, rel: ConfPath
    ):
        fst, rem = rel.split_front()
        relp = ConfPath((fst,))
        for p in rem.pth:
            if not overridden_values.set_value_default(relp, {}):
                return False
            relp = relp.join(p)
        default: Any = {} if ref.sub_options else None
        return overridden_values.set_value_default(relp, default)
