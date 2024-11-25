from __future__ import annotations

import logging
from copy import copy, deepcopy
from dataclasses import dataclass
from typing import List, Union, cast

from ...common import ConfigError
from .config_option import ConfigOption
from .config_path import ConfPath
from .value_reference import OverrideActionEnum, ValueReference

logger = logging.getLogger(__name__)


@dataclass
class CMakeOption:
    clear: bool = False
    value: list[str | bool] | None = None
    append: list[str | bool] | None = None
    prepend: list[str | bool] | None = None
    remove: list[str | bool] | None = None
    datatype: str | None = None
    strict: bool = False

    @classmethod
    def create(cls, x, datatype=None):
        assert datatype is None or isinstance(datatype, str)
        if isinstance(x, list):
            assert all(isinstance(e, (bool, str)) for e in x)
            return cls(value=x, datatype=datatype)
        assert isinstance(x, (bool, str))
        return cls(value=[x], datatype=datatype)

    @classmethod
    def _from_dict(cls, x: dict[str, str | bool | list[str | bool]], pth: ConfPath):
        opt = cls()
        if "=" in x:
            assert "value" not in x
            x["value"] = x.pop("=")
        if "+" in x:
            assert "append" not in x
            x["append"] = x.pop("+")
        if "-" in x:
            assert "remove" not in x
            x["remove"] = x.pop("-")
        all_bool = True
        nonempty = False
        # Preserve lists and convert all values to singletons
        for k in ("value", "append", "remove", "prepend"):
            if k not in x:
                continue
            v = x.pop(k)
            v = v if isinstance(v, list) else [v]
            if not all(isinstance(b, bool) for b in v):
                all_bool = False
            if len(v) > 0:
                nonempty = True
            setattr(opt, k, v)
        # Determine the data type
        datatype = x.pop("type", None)
        if datatype is None and all_bool and nonempty:
            datatype = "BOOL"
        if datatype is not None and not isinstance(datatype, str):
            msg = f'Error in {pth}: Type of "type" should be str, '
            msg += f"not {type(datatype)}"
            raise ConfigError(msg)
        opt.datatype = datatype
        # Check if the data type should be checked in strict mode or not
        strict = x.pop("strict", True)
        if not isinstance(strict, bool):
            msg = f'Error in {pth}: Type of "strict" should be bool, '
            msg += f"not {type(strict)}"
            raise ConfigError(msg)
        opt.strict = strict
        # Check if there are any unused keys left
        assert not x
        return opt

    @classmethod
    def from_values(cls, values: ValueReference):
        val = values.values
        if values.action == OverrideActionEnum.Clear:
            assert val is None
            return cls(clear=True)
        if isinstance(val, dict):
            return cls._from_dict(val, values.value_path)
        datatype = None
        if isinstance(val, bool):
            val = [val]
            datatype = "BOOL"
        elif isinstance(val, str):
            val = [val]
        elif isinstance(val, list):
            assert all(isinstance(b, (str, bool)) for b in val)
            all_bool = all(isinstance(b, bool) for b in val)
            nonempty = len(val) > 0
            if all_bool and nonempty:
                datatype = "BOOL"
        else:
            msg = f"Invalid type {type(val)}"
            raise AssertionError(msg)
        val = cast(List[Union[str, bool]], val)
        if values.action in (OverrideActionEnum.Default, OverrideActionEnum.Assign):
            return cls(value=val, datatype=datatype)
        if values.action == OverrideActionEnum.Remove:
            return cls(remove=val, datatype=datatype)
        if values.action == OverrideActionEnum.Append:
            return cls(append=val, datatype=datatype)
        if values.action == OverrideActionEnum.Prepend:
            return cls(prepend=val, datatype=datatype)
        msg = f"Invalid action {values.action}"
        raise AssertionError(msg)

    @staticmethod
    def _combine_types(
        a: CMakeOption,
        b: CMakeOption,
        strict: bool,
        a_path: ConfPath,
        b_path: ConfPath,
    ) -> str | None:
        def report(msg):
            if not strict:
                logger.warning(msg)
                return b.datatype
            msg = f'{msg} (use "strict" = false to ignore)'
            raise ConfigError(msg)

        if b.datatype is None:
            return a.datatype
        if a.datatype is None:
            return b.datatype
        if a.datatype == b.datatype:
            return b.datatype
        msg = "Incompatible types when overriding or inheriting CMake settings"
        # Cannot override these by other types
        if a.datatype in ("BOOL", "STRING", "FILEPATH"):
            return report(f"{msg}: {a.datatype} ({a_path}) and {b.datatype} ({b_path})")
        # PATH can be made more specific to FILEPATH
        if a.datatype == "PATH" and b.datatype != "FILEPATH":
            return report(f"{msg}: {a.datatype} ({a_path}) and {b.datatype} ({b_path})")
        return b.datatype

    def override(self, new: CMakeOption):
        # Clearing always propagates
        if new.clear:
            return copy(new)
        old = copy(self)
        # If we're overriding with a value, the old value is not used
        if new.value is not None:
            old.value = new.value
            old.append = new.append
            old.prepend = new.prepend
            old.remove = []
            return old
        # Otherwise, we're simply appending to or removing from the old value,
        # and these changes are propagated down to the old value.
        if new.remove is not None:
            old.remove = (old.remove or []) + new.remove
            if old.value:
                old.value = [e for e in old.value if e not in new.remove]
            if old.prepend:
                old.prepend = [e for e in old.prepend if e not in new.remove]
            if old.append:
                old.append = [e for e in old.append if e not in new.remove]
        if new.append is not None:
            old.append = (old.append or []) + new.append
        if new.prepend is not None:
            old.prepend = new.prepend + (old.prepend or [])
        return old

    def finalize(self) -> list[str | bool] | None:
        empty = True
        final = []
        if self.value is not None:
            empty = False
            final = self.value
        if self.append is not None:
            empty = False
            final = final + self.append
        if self.prepend is not None:
            empty = False
            final = self.prepend + final
        return None if (empty and self.clear) else final


# Entries are of the following form
# {
#    "VAR_A": "value",
#    "VAR_B": ["123", "456"],
#    "VAR_C": false,
#    "VAR_D": {
#       "type": "STRING",
#       "value": ["789", "xyz"],
#    },
#    "VAR_E": {
#       "type": "FILEPATH",
#       "value": "/usr/bin/bash",
#    },
#    "VAR_F": {
#       "type": "FILEPATH",
#       "append": ["/usr/bin/bash"],
#    }
# }


class CMakeOptConfigOption(ConfigOption):
    """
    Dictionary of CMake options, with optional data type, ability to merge
    or remove options, etc.
    """

    valid_keys = frozenset(
        ("+", "-", "=", "append", "remove", "value", "prepend", "type", "strict")
    )

    def get_typename(self, md: bool = False) -> str:
        return "dict (CMake)"

    @staticmethod
    def _check_type(a, a_path):
        valid_types = (None, "STRING", "BOOL", "PATH", "FILEPATH")
        if a not in valid_types:
            msg = f"Unknown type '{a}' in {a_path}"
            raise ConfigError(msg)

    def _combine(self, a: CMakeOption, b: CMakeOption, a_path, b_path):
        r = a.override(b)
        r.datatype = CMakeOption._combine_types(a, b, b.strict, a_path, b_path)
        return r

    def override(self, old_value: ValueReference, new_value: ValueReference):
        if new_value.values is None:
            return None
        if old_value.values is None:
            old_value.values = {}
        r = deepcopy(old_value.values)
        for k, v in new_value.values.items():
            if k not in r:
                r[k] = deepcopy(v)
            else:
                r[k] = self._combine(
                    a=r[k],
                    b=v,
                    a_path=old_value.value_path.join(k),
                    b_path=new_value.value_path.join(k),
                )
        return r

    def _verify_cmake_list(self, values: ValueReference):
        if isinstance(values.values, list):
            for v in values.values:
                if not isinstance(v, str) and not isinstance(v, bool):
                    msg = f"Type of values in list {values.value_path} should "
                    msg += f"be str or bool, not {type(v)}"
                    raise ConfigError(msg)
        elif not isinstance(values.values, str) and not isinstance(values.values, bool):
            msg = f"Type of values in {values.value_path} should be str or bool or a "
            msg += f"list thereof, not {type(values.values)}"
            raise ConfigError(msg)

    def _verify_cmake_list_or_dict(self, values: ValueReference):
        if isinstance(values.values, dict):
            for k in values.values:
                if not isinstance(k, str):
                    msg = f"Type of keys in {values.value_path} should be str, "
                    msg += f"not {type(k)}"
                    raise ConfigError(msg)
                self._verify_cmake_list(values.sub_ref(k))
        else:
            self._verify_cmake_list(values)

    def _check_dict_keys(self, d, pth: ConfPath):
        if not isinstance(d, dict):
            return
        invalid_keys = set(d) - self.valid_keys
        if invalid_keys:
            msg = f"Invalid keys in {pth}: {list(invalid_keys)}"
            raise ConfigError(msg)
        if "value" in d and "=" in d:
            msg = f"Invalid keys in {pth}: "
            msg += 'Cannot combine "value" and "="'
            raise ConfigError(msg)
        if "append" in d and "+" in d:
            msg = f"Invalid keys in {pth}: "
            msg += 'Cannot combine "append" and "+"'
            raise ConfigError(msg)
        if "remove" in d and "-" in d:
            msg = f"Invalid keys in {pth}: "
            msg += 'Cannot combine "remove" and "-"'
            raise ConfigError(msg)
        if "value" in d or "=" in d:
            invalid_keys = {"+", "append", "-", "remove", "prepend"} & set(d)
            if invalid_keys:
                msg = f"Invalid keys in {pth}: "
                msg += 'Cannot combine "value" or "=" with the '
                msg += f"following keys: {list(invalid_keys)}"
                raise ConfigError(msg)
        if "type" in d:
            self._check_type(d["type"], pth)

    def verify(self, values: ValueReference):
        """Checks the data types and keys of the values, and then converts
        them to a dictionary of CMakeOptions."""
        if values.values is None:
            return None
        if values.action not in (OverrideActionEnum.Append, OverrideActionEnum.Default):
            msg = f"Option {values.value_path} of type {self.get_typename()} "
            msg += f"does not support operation {values.action.value}"
            raise ConfigError(msg)
        if not isinstance(values.values, dict):
            msg = f"Type of {values.value_path} should be {dict}, "
            msg += f"not {type(values.values)}"
            raise ConfigError(msg)
        elif not all(isinstance(k, str) for k in values.values):
            msg = f"Type of keys in {values.value_path} should be {str}"
            raise ConfigError(msg)
        for k in values.values:
            self._verify_cmake_list_or_dict(values.sub_ref(k))

        valdict: dict[str, CMakeOption] = {}
        for k in values.values:
            pth = values.value_path.join(k)
            self._check_dict_keys(values.values[k], pth)
            valdict[k] = CMakeOption.from_values(values.sub_ref(k))
        return valdict

    def finalize(self, values: ValueReference) -> dict[str, str] | None:
        """Converts the internal dict of CMakeOptions back into a dict of string
        that can be passed as CMake command-line arguments"""
        if values.values is None:
            return None

        def convert(x):
            assert isinstance(x, CMakeOption)
            final = x.finalize()
            if final is None:
                return None
            on_off = {True: "On", False: "Off"}
            escape = lambda x: x.replace(";", "\\;")
            to_str = lambda b: (escape(b) if isinstance(b, str) else on_off[b])
            return ";".join(map(to_str, final))

        def convert_key(k, x):
            assert isinstance(x, CMakeOption)
            return f"{k}:{x.datatype}" if x.datatype else k

        options: dict[str, str] = {}
        for k, v in values.values.items():
            if v is not None:
                str_v = convert(v)
                if str_v is not None:
                    options[convert_key(k, v)] = str_v
        return options
