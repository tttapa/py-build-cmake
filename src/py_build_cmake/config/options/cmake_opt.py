from __future__ import annotations

import logging
from copy import copy, deepcopy
from dataclasses import dataclass

from ...common import ConfigError
from .config_path import ConfPath
from .dict import DictOfStrConfigOption
from .value_reference import OverrideAction, OverrideActionEnum, ValueReference

logger = logging.getLogger(__name__)


@dataclass
class CMakeOption:
    value: list[str | bool] | None = None
    append: list[str | bool] | None = None
    prepend: list[str | bool] | None = None
    remove: list[str | bool] | None = None
    datatype: str | None = None
    strict: bool = True

    @classmethod
    def create(cls, x, datatype=None):
        assert datatype is None or isinstance(datatype, str)
        if isinstance(x, list):
            assert all(isinstance(e, (bool, str)) for e in x)
            return cls(value=x, datatype=datatype)
        assert isinstance(x, (bool, str))
        return cls(value=[x], datatype=datatype)


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


class CMakeOptConfigOption(DictOfStrConfigOption):
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
    def _convert_to_option(
        x: str | bool | list[str | bool] | dict[str, str | bool | list[str | bool]],
        pth: ConfPath,
    ):
        if isinstance(x, bool):
            return CMakeOption(value=[x], datatype="BOOL")
        if isinstance(x, str):
            return CMakeOption(value=[x])
        if isinstance(x, list):
            all_bool = all(isinstance(b, bool) for b in x)
            nonempty = len(x) > 0
            return CMakeOption(
                value=x,
                datatype=("BOOL" if all_bool and nonempty else None),
            )
        assert isinstance(x, dict)
        return CMakeOptConfigOption._convert_dict_to_option(x, pth)

    @staticmethod
    def _convert_dict_to_option(
        x: dict[str, str | bool | list[str | bool]], pth: ConfPath
    ):
        opt = CMakeOption()
        if "=" in x:
            x["value"] = x.pop("=")
        if "+" in x:
            x["append"] = x.pop("+")
        if "-" in x:
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
        if x:
            msg = f"Error in {pth}: Invalid keys: {list(x)}"
            raise ConfigError(msg)
        return opt

    @staticmethod
    def _check_type(a, a_path):
        valid_types = (None, "STRING", "BOOL", "PATH", "FILEPATH")
        if a not in valid_types:
            msg = f"Unknown type '{a}' in {a_path}"
            raise ConfigError(msg)

    def _combine_types(
        self,
        a: str | None,
        b: str | None,
        strict: bool,
        a_path: ConfPath,
        b_path: ConfPath,
    ):
        def report(msg):
            if not strict:
                logger.warning(msg)
                return b
            msg = f'{msg} (use "strict" = false to ignore)'
            raise ConfigError(msg)

        if b is None:
            return a
        if a is None:
            return b
        if a == b:
            return b
        msg = "Incompatible types when overriding or inheriting CMake settings"
        # Cannot override these by other types
        if a in ("BOOL", "STRING", "FILEPATH"):
            return report(f"{msg}: {a} ({a_path}) and {b} ({b_path})")
        # PATH can be made more specific to FILEPATH
        if a == "PATH" and b != "FILEPATH":
            return report(f"{msg}: {a} ({a_path}) and {b} ({b_path})")
        return b

    def _combine_values_into(self, a: CMakeOption, b: CMakeOption):
        if a.value is None:
            if b.value is not None:
                a.value = b.value
            if b.remove is not None:
                a.remove = b.remove
            if b.prepend is not None:
                a.prepend = b.prepend + (a.prepend or [])
            if b.append is not None:
                a.append = (a.append or []) + b.append
        else:
            if b.remove is not None:
                remove = set(b.remove)
                a.value = [v for v in a.value if v not in remove]
            if b.value is not None:
                a.value = b.value
            if b.append is not None:
                a.value = a.value + b.append
            if b.prepend is not None:
                a.value = b.prepend + a.value

    def _combine(self, a: CMakeOption, b: CMakeOption, a_path, b_path):
        if b.value is not None:
            return b
        a = copy(a)
        a.datatype = self._combine_types(
            a.datatype, b.datatype, b.strict, a_path, b_path
        )
        self._combine_values_into(a, b)
        return a

    def override(self, old_value: ValueReference, new_value: ValueReference):
        if old_value.values is None:
            old_value.values = {}
        if new_value.values is None:
            return old_value.values
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

    def _verify_cmake_list(self, x, pth: ConfPath):
        if isinstance(x, list):
            for v in x:
                if not isinstance(v, str) and not isinstance(v, bool):
                    msg = f"Type of values in list {pth} should be str or "
                    msg += f"bool, not {type(v)}"
                    raise ConfigError(msg)
        elif not isinstance(x, str) and not isinstance(x, bool):
            msg = f"Type of values in {pth} should be str or bool or a "
            msg += f"list thereof, not {type(x)}"
            raise ConfigError(msg)

    def _verify_cmake_list_or_dict(self, x, pth: ConfPath):
        if isinstance(x, dict):
            for k, v in x.items():
                if not isinstance(k, str):
                    msg = f"Type of keys in {pth} should be str, "
                    msg += f"not {type(k)}"
                    raise ConfigError(msg)
                self._verify_cmake_list(v, pth.join(k))
        else:
            self._verify_cmake_list(x, pth)

    def _convert_override_to_dict(self, x: OverrideAction, pth: ConfPath):
        def raise_err():
            msg = f"Option {pth} does not support operation "
            msg += f"{x.action.value}"
            raise ConfigError(msg)

        v = x.values
        OAE = OverrideActionEnum
        return {
            OAE.Default: lambda: v,
            OAE.Assign: lambda: v if isinstance(v, dict) else {"value": v},
            OAE.Append: lambda: {"append": v},
            OAE.Prepend: lambda: {"prepend": v},
            OAE.Remove: lambda: {"-": v},
            OAE.AppendPath: lambda: raise_err(),
            OAE.PrependPath: lambda: raise_err(),
        }[x.action]()

    def _check_dict_keys(self, d, pth):
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
        if values.action not in (OverrideActionEnum.Assign, OverrideActionEnum.Default):
            msg = f"Option {values.value_path} of type {self.get_typename()} "
            msg += f"does not support operation {values.action.value}"
            raise ConfigError(msg)
        if values.values is None:
            return None
        valdict = copy(values.values)
        if not isinstance(valdict, dict):
            msg = f"Type of {values.value_path} should be {dict}, "
            msg += f"not {type(valdict)}"
            raise ConfigError(msg)
        elif not all(isinstance(k, str) for k in valdict):
            msg = f"Type of keys in {values.value_path} should be {str}"
            raise ConfigError(msg)
        for k, v in valdict.items():
            pth = values.value_path.join(k)
            if isinstance(v, OverrideAction):
                valdict[k] = self._convert_override_to_dict(v, pth)
            self._verify_cmake_list_or_dict(valdict[k], pth)

        for k in valdict:
            pth = values.value_path.join(k)
            self._check_dict_keys(valdict[k], pth)
            valdict[k] = self._convert_to_option(valdict[k], pth)
        return valdict

    def finalize(self, values: ValueReference) -> dict[str, str]:
        """Converts the internal dict of CMakeOptions back into a dict of string
        that can be passed as CMake command-line arguments"""

        def convert(x):
            assert isinstance(x, CMakeOption)
            y = CMakeOption(value=[])
            self._combine_values_into(y, x)
            assert y.value is not None
            on_off = {True: "On", False: "Off"}
            escape = lambda x: x.replace(";", "\\;")
            to_str = lambda b: (escape(b) if isinstance(b, str) else on_off[b])
            return ";".join(map(to_str, y.value))

        def convert_key(k, x):
            assert isinstance(x, CMakeOption)
            return f"{k}:{x.datatype}" if x.datatype else k

        options: dict[str, str] = {}
        for k, v in values.values.items():
            options[convert_key(k, v)] = convert(v)
        return options
