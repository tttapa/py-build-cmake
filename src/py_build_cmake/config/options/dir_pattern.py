from __future__ import annotations

import os.path as osp
import re
from copy import copy
from pathlib import PurePath

from ...common import ConfigError
from .config_path import ConfPath
from .default import DefaultValue
from .list import ListOfStrConfigOption, ListOption
from .value_reference import ValueReference


class DirPatternsConfigOption(ListOfStrConfigOption):
    def __init__(
        self,
        name: str,
        description: str = "",
        example: str = "",
        default: DefaultValue | None = None,
        inherit_from: ConfPath | str | None = None,
        create_if_inheritance_target_exists: bool = False,
        convert_str_to_singleton=False,
    ) -> None:
        super().__init__(
            name,
            description,
            example,
            default,
            inherit_from,
            create_if_inheritance_target_exists,
            convert_str_to_singleton,
        )

    def _verify_pattern_list(self, values: list[str], pth: ConfPath):
        # Based on https://github.com/pypa/flit/blob/f7496a50debdfa393e39f8e51d328deabcd7ae7e/flit_core/flit_core/config.py#L215
        pattern_list = copy(values)
        # Windows filenames can't contain these (nor * or ?, but they are part of
        # glob patterns) - https://stackoverflow.com/a/31976060/434217
        bad_chars = re.compile(r'[\000-\037<>:"\\]')
        for i, pattern in enumerate(pattern_list):
            if bad_chars.search(pattern):
                msg = f"Pattern '{pattern}' in {pth} contains bad characters (<>:\"\\ or control characters)"
                raise ConfigError(msg)
            # Normalize the path
            normp = PurePath(osp.normpath(pattern))
            # Make sure that the path is relative and inside of the project
            if normp.is_absolute():
                msg = f"Pattern '{pattern}' in {pth} should be relative"
                raise ConfigError(msg)
            if normp.parts[0] == "..":
                msg = f"Pattern '{pattern}' in {pth} cannot refer to the parent directory (..)"
                raise ConfigError(msg)
            pattern_list[i] = str(normp)
        return pattern_list

    def verify(self, values: ValueReference):
        v = super().verify(values)
        assert isinstance(v, ListOption)
        if v.value:
            v.value = self._verify_pattern_list(v.value, values.value_path)
        if v.append:
            v.append = self._verify_pattern_list(v.append, values.value_path)
        if v.prepend:
            v.prepend = self._verify_pattern_list(v.prepend, values.value_path)
        if v.remove:
            v.remove = self._verify_pattern_list(v.remove, values.value_path)
        return v
