from __future__ import annotations

import os
from copy import copy
from dataclasses import dataclass, fields

from ...common import ConfigError
from .config_option import ConfigOption
from .value_reference import OverrideActionEnum, ValueReference


@dataclass
class StringOption:
    clear: bool = False
    value: str | None = None
    append: str | None = None
    append_path: str | None = None
    prepend: str | None = None
    prepend_path: str | None = None
    remove: list[str] | None = None

    @classmethod
    def create(cls, value: str):
        return cls(value=value)

    @classmethod
    def from_values(cls, values: ValueReference):  # noqa: PLR0911
        val = values.values
        if values.action == OverrideActionEnum.Clear:
            assert val is None
            return cls(clear=True)
        # The value should be a string, unless it's a "remove" action, then
        # list[str] is also fine
        msg = f"Type of {values.value_path} should be {str}, "
        msg += f"not {type(values.values)}"
        if values.action == OverrideActionEnum.Remove:
            if isinstance(val, list):
                if not all(isinstance(v, str) for v in val):
                    raise ConfigError(msg)
            elif not isinstance(val, str):
                raise ConfigError(msg)
            val_list: list[str] = val if isinstance(val, list) else [val]
            return cls(remove=val_list)
        if not isinstance(val, str):
            raise ConfigError(msg)
        if values.action in (OverrideActionEnum.Default, OverrideActionEnum.Assign):
            return cls(value=val)
        if values.action == OverrideActionEnum.Append:
            return cls(append=val)
        if values.action == OverrideActionEnum.AppendPath:
            return cls(append_path=val)
        if values.action == OverrideActionEnum.Prepend:
            return cls(prepend=val)
        if values.action == OverrideActionEnum.PrependPath:
            return cls(prepend_path=val)
        msg = f"Invalid action {values.action}"
        raise AssertionError(msg)

    @staticmethod
    def _join_path(a, b):
        return a + os.pathsep + b if a and b else a + b

    def override(self, new: StringOption):  # noqa: PLR0912
        # Clearing always propagates
        if new.clear:
            return copy(new)
        old = copy(self)
        # If we're overriding with a value, the old value is not used
        if new.value is not None:
            old.value = new.value
            old.append = new.append
            old.append_path = new.append_path
            old.prepend = new.prepend
            old.prepend_path = new.prepend_path
            old.remove = []
            return old
        # Otherwise, we're simply appending to or removing from the old value,
        # and these changes are propagated down to the old value.
        if new.remove is not None:
            old.remove = (old.remove or []) + new.remove
            for r in new.remove:
                if old.value:
                    old.value = old.value.replace(r, "")
                if old.prepend:
                    old.prepend = old.prepend.replace(r, "")
                if old.prepend_path:
                    old.prepend_path = old.prepend_path.replace(r, "")
                if old.append:
                    old.append = old.append.replace(r, "")
                if old.append_path:
                    old.append_path = old.append_path.replace(r, "")
        if new.append is not None:
            old.append = (old.append or "") + new.append
        if new.append_path is not None:
            old.append_path = self._join_path(old.append_path or "", new.append_path)
        if new.prepend is not None:
            old.prepend = new.prepend + (old.prepend or "")
        if new.prepend_path is not None:
            old.prepend_path = self._join_path(new.prepend_path, old.prepend_path or "")
        return old

    def finalize(self) -> str | None:
        empty = True
        final = ""
        # TODO: combining append and append_path may result in weird order
        if self.value is not None:
            empty = False
            final = self.value
        if self.append is not None:
            empty = False
            final = final + self.append
        if self.append_path is not None:
            empty = False
            final = StringOption._join_path(final, self.append_path)
        if self.prepend is not None:
            empty = False
            final = self.prepend + final
        if self.prepend_path is not None:
            empty = False
            final = StringOption._join_path(self.prepend_path, final)
        return None if (empty and self.clear) else final

    def __repr__(self):
        attrs = {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not None
        }
        if not attrs["clear"]:
            del attrs["clear"]
        attr_str = ", ".join(f"{key}={value!r}" for key, value in attrs.items())
        return f"{self.__class__.__name__}({attr_str})"


class StringConfigOption(ConfigOption):
    def get_typename(self, md: bool = False) -> str:
        return "string"

    def verify(self, values: ValueReference):
        return StringOption.from_values(values)

    def override(self, old_value, new_value):
        new, old = new_value.values, copy(old_value.values)
        if old is None:  # No previous value
            old = StringOption()
        assert isinstance(new, StringOption)
        assert isinstance(old, StringOption)
        return old.override(new)

    def finalize(self, values: ValueReference):
        if values.values is None:
            return None
        val = values.values
        if isinstance(val, str):
            return val
        assert isinstance(val, StringOption)
        return val.finalize()
