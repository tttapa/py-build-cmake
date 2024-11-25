from pprint import pprint

from py_build_cmake.config.options.config_option import ConfigOption, MultiConfigOption
from py_build_cmake.config.options.config_path import ConfPath
from py_build_cmake.config.options.config_reference import ConfigReference
from py_build_cmake.config.options.finalize import ConfigFinalizer
from py_build_cmake.config.options.override import ConfigOverrider
from py_build_cmake.config.options.string import StringConfigOption
from py_build_cmake.config.options.value_reference import (
    ValueReference,
)
from py_build_cmake.config.options.verify import ConfigVerifier


def gen_test_opts():
    leaf11 = StringConfigOption("leaf11")
    leaf12 = StringConfigOption("leaf12")
    mid1 = MultiConfigOption("mid1")
    mid1.insert(leaf11)
    mid1.insert(leaf12)
    trunk = ConfigOption("trunk")
    trunk.insert(mid1)
    opts = ConfigOption("root")
    opts.insert(trunk)
    return opts


def test_override0():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "*1",
                "leaf12": "*2",
                "0": {"leaf11": "11", "leaf12": "12"},
                "10": {"leaf11": "111"},
                "20": {},
            },
        },
    }
    override_values = {}  # No override
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    pprint(rval.values)
    override_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=rval,
        new_values=ValueReference(ConfPath.from_string("/"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/"), overridden_values),
    ).finalize()

    assert finalized_values == {
        "trunk": {
            "mid1": {
                "0": {
                    "leaf11": "11",
                    "leaf12": "12",
                },
                "10": {
                    "leaf11": "111",
                    "leaf12": "*2",
                },
                "20": {
                    "leaf11": "*1",
                    "leaf12": "*2",
                },
            },
        },
    }


def test_override1():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "*1",
                "leaf12": "*2",
                "0": {"leaf11": "11", "leaf12": "12"},
                "10": {
                    "leaf11": "111",
                },
            },
        },
    }
    override_values = {
        "trunk": {
            "mid1": {
                "leaf11": "-1*",
                "10": {"leaf12": "-12"},
                "20": {"leaf11": "1111"},
                "30": {},
            },
        },
    }  # No override
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    pprint(rval.values)
    override_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    pprint(override_values)
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=rval,
        new_values=ValueReference(ConfPath.from_string("/"), override_values),
    ).override()
    pprint(overridden_values)
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/"), overridden_values),
    ).finalize()

    assert finalized_values == {
        "trunk": {
            "mid1": {
                "0": {
                    "leaf11": "11",
                    "leaf12": "12",
                },
                "10": {
                    "leaf11": "111",
                    "leaf12": "-12",
                },
                "20": {
                    "leaf11": "1111",
                    "leaf12": "*2",
                },
                "30": {
                    "leaf11": "-1*",
                    "leaf12": "*2",
                },
            },
        },
    }
