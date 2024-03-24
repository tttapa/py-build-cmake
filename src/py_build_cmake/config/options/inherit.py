from __future__ import annotations

from .config_path import ConfPath
from .config_reference import ConfigReference
from .override import ConfigOverrider
from .value_reference import ValueReference


class ConfigInheritor:
    def __init__(
        self,
        root: ConfigReference,
        root_values: ValueReference,
        ref: ConfigReference | None = None,
        value_path: ConfPath | None = None,
        done: set[tuple[str, ...]] | None = None,
    ) -> None:
        if ref is None:
            ref = root
        if value_path is None:
            value_path = ConfPath()
        if done is None:
            done = set()
        self.root = root
        self.root_values = root_values
        self.ref = ref
        self.value_path = value_path
        self.done = done

    def _inherit_self(self):
        # Check if this option inherits from another option
        inherits = self.ref.config.inherits
        if inherits is None:
            return
        # Only carry out the inheritance once
        if self.value_path.pth in self.done:
            return
        self.done.add(self.value_path.pth)
        # Find the option we inherit from
        super = self.ref.resolve_inheritance_single(self.root)
        # If the option we're inheriting from does not have its value set,
        # don't do anything.
        try:
            super_value = self.root_values.sub_ref(super.config_path)
        except KeyError:
            return
        # If our option does not have its value set, create this value and
        # all its parents.
        if not self._create_parent_values():
            return

        # If our super option inherits from other options, carry out that
        # inheritance first.
        ConfigInheritor(
            root=self.root,
            root_values=self.root_values,
            ref=super,
            value_path=super.config_path,
            done=self.done,
        )._inherit_self()
        # Note that we only detect direct inheritance, inheriting from a
        # subtree that is part of an inherited tree is not supported (and
        # and unnecessary for the current schema)

        # Create a copy of the values of our super option and override them
        # with our own values
        new_values = self.root_values.sub_ref(self.value_path)
        assert new_values is not None
        real_config = super.resolve_inheritance(self.root)
        inherited_values = ConfigOverrider(
            root=self.root,
            ref=real_config,
            values=super_value,
            new_values=new_values,
        ).override()
        self.root_values.set_value(self.value_path, inherited_values)

    def _create_parent_values(self):
        """
        Loop over all parent options of path in the root and default-initialize
        their values to an empty dict if the option's
        create_if_inheritance_target_exists member is set to True.
        """
        sub, val = self.root, self.root_values
        for s in self.value_path.pth:
            sub = sub.sub_ref(s)
            try:
                val = val and val.sub_ref(s)
            except KeyError:
                if not sub.config.create_if_inheritance_target_exists:
                    return False
                val = None
        val = self.root_values
        for s in self.value_path.pth:
            val.values.setdefault(s, {})
            val = val.sub_ref(s)
            assert val is not None
        return True

    def inherit(self):
        self._inherit_self()
        for name in self.ref.sub_options:
            ref = self.ref.sub_ref(name)
            val_path = self.value_path.join(name)
            ConfigInheritor(
                root=self.root,
                root_values=self.root_values,
                ref=ref,
                value_path=val_path,
                done=self.done,
            ).inherit()
