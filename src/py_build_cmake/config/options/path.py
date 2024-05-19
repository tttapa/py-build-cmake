from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ...common import ConfigError
from .config_path import ConfPath
from .default import DefaultValue
from .string import StringConfigOption
from .value_reference import ValueReference


@dataclass
class RelativeToCurrentConfig:
    project_path: Path | PurePosixPath
    description: str = "current configuration file"


@dataclass
class RelativeToProject:
    project_path: Path | PurePosixPath
    description: str = "project directory"


class PathConfigOption(StringConfigOption):
    def __init__(
        self,
        name: str,
        description: str = "",
        example: str = "",
        default: DefaultValue | None = None,
        inherit_from: ConfPath | str | None = None,
        create_if_inheritance_target_exists: bool = False,
        must_exist: bool = True,
        expected_contents: list[str] | None = None,
        base_path: RelativeToProject | RelativeToCurrentConfig | None = None,
        allow_abs: bool = False,
        is_folder: bool = True,
    ):
        if expected_contents is None:
            expected_contents = []
        super().__init__(
            name,
            description,
            example,
            default,
            inherit_from,
            create_if_inheritance_target_exists,
        )
        self.must_exist = must_exist or bool(expected_contents)
        self.expected_contents = expected_contents
        self.base_path = base_path
        self.allow_abs = allow_abs
        self.is_folder = is_folder
        if self.base_path:
            assert self.base_path.project_path.is_absolute()

    def get_typename(self, md: bool = False):
        return "path" if self.is_folder else "filepath"

    def check_path(self, values: ValueReference):
        assert isinstance(values.values, str)
        path: Path | PurePosixPath = Path(values.values)
        # Absolute or relative path?
        if path.is_absolute():
            # Absolute path
            if not self.allow_abs:
                msg = f'{values.value_path}: "{path!s}" must be a relative path'
                raise ConfigError(msg)
        # Relative path
        elif isinstance(self.base_path, RelativeToCurrentConfig):
            # value_path[0] is relative for files inside of the project,
            # otherwise it is absolute
            path = Path(PurePosixPath(values.value_path.pth[0]).parent / path)
            if not path.is_absolute():
                path = self.base_path.project_path / path
        elif isinstance(self.base_path, RelativeToProject):
            path = self.base_path.project_path / path
        else:
            msg = "Invalid relative path type"
            raise AssertionError(msg)
        assert path.is_absolute(), f"Failed to make path absolute: {path!s}"
        # Does the path exist?
        if self.must_exist:
            path = Path(path)
            if not path.exists():
                msg = f'{values.value_path}: "{path!s}" does not exist'
                raise ConfigError(msg)
            if self.is_folder != path.is_dir():
                type_ = "directory" if self.is_folder else "file"
                msg = f'{values.value_path}: "{path!s}" should be a {type_}'
                raise ConfigError(msg)
            # Are any of the required contents missing?
            missing = [
                sub for sub in self.expected_contents if not (path / Path(sub)).exists()
            ]
            if missing:
                missingstr = '", "'.join(missing)
                msg = f'{values.value_path}: "{path!s}" does not contain the following required files or folders: "{missingstr}"'
                raise ConfigError(msg)
        return path.resolve() if isinstance(path, Path) else path

    def verify(self, values: ValueReference):
        values.values = super().verify(values)
        return self.check_path(values)
