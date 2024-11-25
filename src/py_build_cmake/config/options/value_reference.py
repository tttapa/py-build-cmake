from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .config_path import ConfPath


class OverrideActionEnum(Enum):
    Default = "?="
    Assign = "="
    Append = "+="
    AppendPath = "+=(path)"
    Prepend = "=+"
    PrependPath = "=+(path)"
    Remove = "-="
    Clear = "=!"

    def override_string(self, old: str, new: str) -> str:
        return {
            OverrideActionEnum.Default: lambda: new,
            OverrideActionEnum.Assign: lambda: new,
            OverrideActionEnum.Append: lambda: old + new,
            OverrideActionEnum.AppendPath: lambda: (
                old + os.pathsep + new if old and new else old + new
            ),
            OverrideActionEnum.Prepend: lambda: new + old,
            OverrideActionEnum.PrependPath: lambda: (
                new + os.pathsep + old if old and new else old + new
            ),
            OverrideActionEnum.Remove: lambda: old.replace(new, ""),
        }[self]()


@dataclass
class OverrideAction:
    action: OverrideActionEnum
    values: Any


class ValueReference:
    def __init__(
        self,
        value_path: ConfPath,
        values: dict | OverrideAction | Any,
        action: OverrideActionEnum = OverrideActionEnum.Default,
    ) -> None:
        self.value_path = value_path
        self.action = action
        self.values: dict | Any
        if isinstance(values, OverrideAction):
            self.action = values.action
            self.values = values.values
        else:
            self.values = values

    def is_value_set(self, path: str | ConfPath):
        values = self.values
        if values is None:
            return False
        if isinstance(path, str):
            return path in values
        while path:
            name, path = path.split_front()
            if values is None or name not in values:
                return False
            values = values[name]
        return True

    def get_value(self, path: str | ConfPath):
        values = self.values
        if isinstance(path, str):
            if values is None:
                raise KeyError(path)
            return values[path]
        while path:
            name, path = path.split_front()
            if values is None:
                raise KeyError(name)
            values = values[name]
        return values

    def set_value(self, path: str | ConfPath, val: Any):
        values = self.values
        if isinstance(path, str):
            if values is None:
                return False
            values[path] = val
            return True
        while True:
            if values is None:
                return False
            name, path = path.split_front()
            if not path:
                values[name] = val
                return True
            if name not in values:
                return False
            values = values[name]

    def clear_value(self, path: str | ConfPath):
        values = self.values
        if isinstance(path, str):
            if values is None:
                return
            values.pop(path, None)
            return
        while True:
            name, path = path.split_front()
            if values is None:
                return
            if not path:
                values.pop(name, None)
                return
            if name not in values:
                return
            values = values[name]

    def set_value_default(self, path: str | ConfPath, val: Any):
        if self.values is None:
            return None
        if isinstance(path, str):
            self.values.setdefault(path, val)
            return True
        values = self.values
        while True:
            if values is None:
                return False
            name, path = path.split_front()
            if not path:
                values.setdefault(name, val)
                return True
            if name not in values:
                return False
            values = values[name]

    def sub_ref(self, name: str | ConfPath) -> ValueReference:
        if isinstance(name, ConfPath) and len(name.pth) == 1:
            name = name.pth[0]
        if isinstance(name, str):
            if not self.is_value_set(name):
                raise KeyError(name)
            return ValueReference(
                value_path=self.value_path.join(name),
                values=self.values[name],
            )
        if not name:
            return self
        name, rem = name.split_front()
        return self.sub_ref(name).sub_ref(rem)

    def __repr__(self) -> str:
        return f"<ValueReference to: '{self.value_path}'>"
