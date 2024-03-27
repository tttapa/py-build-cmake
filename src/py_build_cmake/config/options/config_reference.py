from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config_option import ConfigOption
from .config_path import ConfPath


class ConfigReference:
    def __init__(self, config_path: ConfPath, config: ConfigOption) -> None:
        self.config_path = config_path
        self.config = config

    @property
    def sub_options(self):
        return self.config.sub_options

    def sub_ref(self, name: str | ConfPath) -> ConfigReference:
        if isinstance(name, ConfPath) and len(name.pth) == 1:
            name = name.pth[0]
        if isinstance(name, str):
            return ConfigReference(
                config_path=self.config_path.join(name),
                config=self.config.sub_options[name],
            )
        name, rem = name.split_front()
        return self.sub_ref(name).sub_ref(rem)

    def resolve_inheritance_single(self, root: ConfigReference) -> ConfigReference:
        if self.config.inherits is None:
            return self
        # Find the option we inherit from and make sure it exists
        parent_path = self.config.inherits
        # TODO: should we support relative paths here?
        # self.config_path.join(self.config.inherits)
        try:
            parent = root.sub_ref(parent_path)
        except KeyError as e:
            msg = f"Inheritance target {parent_path} is not a valid option"
            msg += f" (in {self.config_path})"
            raise ValueError(msg) from e
        return parent

    def resolve_inheritance(self, root: ConfigReference) -> ConfigReference:
        if self.config.inherits is None:
            return self
        return self.resolve_inheritance_single(root).resolve_inheritance(root)
