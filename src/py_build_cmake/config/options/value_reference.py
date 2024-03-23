from __future__ import annotations

from typing import Any

from .config_path import ConfPath


class ValueReference:
    def __init__(self, value_path: ConfPath, values: dict) -> None:
        self.value_path = value_path
        self.values: dict | Any = values

    def is_value_set(self, path: str | ConfPath):
        if isinstance(path, str):
            return path in self.values
        values = self.values
        while path:
            name, path = path.split_front()
            if name not in values:
                return False
            values = values[name]
        return True

    def get_value(self, path: str | ConfPath):
        if isinstance(path, str):
            return self.values[path]
        values = self.values
        while path:
            name, path = path.split_front()
            values = values[name]
        return values

    def set_value(self, path: str | ConfPath, val: Any):
        if isinstance(path, str):
            self.values[path] = val
            return True
        values = self.values
        while True:
            name, path = path.split_front()
            if not path:
                values[name] = val
                return True
            if name not in values:
                return False
            values = values[name]

    def set_value_default(self, path: str | ConfPath, val: Any):
        if isinstance(path, str):
            self.values.setdefault(path, val)
            return True
        values = self.values
        while True:
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
        name, rem = name.split_front()
        return self.sub_ref(name).sub_ref(rem)
