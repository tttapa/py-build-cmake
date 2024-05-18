from pprint import pprint

import pytest
from py_build_cmake.common import ConfigError
from py_build_cmake.config.load import (
    inherit_default_and_finalize_config,
    verify_and_override_config,
)
from py_build_cmake.config.options.cmake_opt import CMakeOptConfigOption
from py_build_cmake.config.options.config_option import ConfigOption
from py_build_cmake.config.options.config_path import ConfPath
from py_build_cmake.config.options.config_reference import ConfigReference
from py_build_cmake.config.options.value_reference import ValueReference


def test_cmake_options_str_list_dict():
    opts = ConfigOption("root")
    trunk = ConfigOption("pyproject.toml")
    cmake = ConfigOption("cmake")
    cmake.insert_multiple(
        [
            CMakeOptConfigOption("opt1"),
            CMakeOptConfigOption("opt2"),
            CMakeOptConfigOption("opt3"),
            CMakeOptConfigOption("opt4"),
            CMakeOptConfigOption("opt5"),
        ]
    )
    trunk.insert(cmake)
    opts.insert(trunk)

    values = {
        "pyproject.toml": {
            "cmake": {
                "opt1": {"FOO1": "bar"},
                "opt2": {"FOO2": ["a", "b"]},
                "opt3": {"FOO3": {"value": "c", "type": "BOOL", "strict": False}},
                "opt4": {"FOO4": {"value": "d"}},
                "opt5": {"FOO5": {"value": ["e", "f"], "type": "STRING"}},
            },
        },
    }

    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), values)
    verify_and_override_config({}, root_ref, root_val)
    inherit_default_and_finalize_config(root_ref, root_val)

    pprint(root_val.values)
    assert root_val.values == {
        "pyproject.toml": {
            "cmake": {
                "opt1": {"FOO1": "bar"},
                "opt2": {"FOO2": "a;b"},
                "opt3": {"FOO3:BOOL": "c"},
                "opt4": {"FOO4": "d"},
                "opt5": {"FOO5:STRING": "e;f"},
            }
        }
    }


def test_cmake_options_wrong_type():
    opts = ConfigOption("root")
    trunk = ConfigOption("pyproject.toml")
    cmake = ConfigOption("cmake")
    cmake.insert(CMakeOptConfigOption("opt1"))
    trunk.insert(cmake)
    opts.insert(trunk)

    values = {"pyproject.toml": {"cmake": {"opt1": {"FOO1": 42}}}}

    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), values)
    expected = r"Type of values in pyproject\.toml/cmake/opt1/FOO1 should be str or bool or a list thereof, not .*int.*"
    with pytest.raises(ConfigError, match=f"^{expected}$"):
        verify_and_override_config({}, root_ref, root_val)

    values = {"pyproject.toml": {"cmake": {"opt1": {"FOO1": [42]}}}}

    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), values)
    expected = r"Type of values in list pyproject\.toml/cmake/opt1/FOO1 should be str or bool, not .*int.*"
    with pytest.raises(ConfigError, match=f"^{expected}$"):
        verify_and_override_config({}, root_ref, root_val)

    values = {"pyproject.toml": {"cmake": {"opt1": {"FOO1": {"value": [42]}}}}}

    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), values)
    expected = r"Type of values in list pyproject\.toml/cmake/opt1/FOO1/value should be str or bool, not .*int.*"
    with pytest.raises(ConfigError, match=f"^{expected}$"):
        verify_and_override_config({}, root_ref, root_val)


def test_cmake_options_invalid_key():
    opts = ConfigOption("root")
    trunk = ConfigOption("pyproject.toml")
    cmake = ConfigOption("cmake")
    cmake.insert(CMakeOptConfigOption("opt1"))
    trunk.insert(cmake)
    opts.insert(trunk)

    values = {"pyproject.toml": {"cmake": {"opt1": {"FOO1": {"valuezzz": "a"}}}}}

    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), values)
    expected = r"Invalid keys in pyproject\.toml/cmake/opt1/FOO1: \['valuezzz'\]"
    with pytest.raises(ConfigError, match=f"^{expected}$"):
        verify_and_override_config({}, root_ref, root_val)

    values = {"pyproject.toml": {"cmake": {"opt1": {"FOO1": {"value": "a", "+": "b"}}}}}

    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), values)
    expected = r'Cannot combine "value" or "=" with the following keys: \[\'\+\'\]'
    with pytest.raises(ConfigError, match=f"^{expected}$"):
        verify_and_override_config({}, root_ref, root_val)


def test_cmake_options_invalid_typename():
    opts = ConfigOption("root")
    trunk = ConfigOption("pyproject.toml")
    cmake = ConfigOption("cmake")
    cmake.insert(CMakeOptConfigOption("opt1"))
    trunk.insert(cmake)
    opts.insert(trunk)

    values = {
        "pyproject.toml": {
            "cmake": {"opt1": {"FOO1": {"value": "a", "type": "STRINGZ"}}}
        }
    }

    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), values)
    expected = r"Unknown type 'STRINGZ' in pyproject\.toml/cmake/opt1/FOO1"
    with pytest.raises(ConfigError, match=f"^{expected}$"):
        verify_and_override_config({}, root_ref, root_val)


def test_cmake_options_override():
    opts = ConfigOption("root")
    trunk = ConfigOption("pyproject.toml")
    cmake = ConfigOption("cmake")
    cmake.insert_multiple(
        [
            CMakeOptConfigOption("opt1"),
            CMakeOptConfigOption("opt2"),
            CMakeOptConfigOption("opt3"),
            CMakeOptConfigOption("opt4"),
            CMakeOptConfigOption("opt5"),
        ]
    )
    trunk.insert(cmake)
    opts.insert(trunk)

    values = {
        "pyproject.toml": {
            "cmake": {
                "opt1": {"FOO1": "bar"},
                "opt2": {"FOO2": ["a", "b"]},
                "opt3": {"FOO3": {"value": "c", "type": "BOOL", "strict": False}},
                "opt4": {"FOO4": {"value": "d"}},
                "opt5": {"FOO5": {"value": ["e", "f"], "type": "STRING"}},
            },
        },
        "override": {
            # Simply combine unrelated options
            "opt1": {"BAR1": "foo"},
            # Override option
            "opt2": {"FOO2": "o"},
            # Append option
            "opt3": {"FOO3": {"append": "x"}},
            # Prepend option
            "opt4": {"FOO4": {"prepend": "y"}},
            # Remove option
            "opt5": {"FOO5": {"-": "f", "+": "g", "type": "STRING"}},
        },
    }

    override = {
        ConfPath.from_string("override"): ConfPath.from_string("pyproject.toml/cmake")
    }
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    root_val = ValueReference(ConfPath.from_string("/"), values)
    verify_and_override_config(override, root_ref, root_val)
    inherit_default_and_finalize_config(root_ref, root_val)

    root_val.values.pop("override")
    pprint(root_val.values)
    assert root_val.values == {
        "pyproject.toml": {
            "cmake": {
                "opt1": {"FOO1": "bar", "BAR1": "foo"},
                "opt2": {"FOO2": "o"},
                "opt3": {"FOO3:BOOL": "c;x"},
                "opt4": {"FOO4": "y;d"},
                "opt5": {"FOO5:STRING": "e;g"},
            }
        }
    }


def test_cmake_options_override_wrong_type():
    pass  # TODO


if __name__ == "__main__":
    test_cmake_options_override()
