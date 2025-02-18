from pprint import pprint
from typing import Any

import pytest

from py_build_cmake.common import ConfigError
from py_build_cmake.config.options.config_option import ConfigOption
from py_build_cmake.config.options.config_path import ConfPath
from py_build_cmake.config.options.config_reference import ConfigReference
from py_build_cmake.config.options.default import (
    ConfigDefaulter,
    DefaultValueValue,
    MissingDefaultError,
    NoDefaultValue,
    RefDefaultValue,
    RequiredValue,
)
from py_build_cmake.config.options.dict import DictOfStrConfigOption
from py_build_cmake.config.options.finalize import ConfigFinalizer
from py_build_cmake.config.options.inherit import ConfigInheritor
from py_build_cmake.config.options.list import ListOfStrConfigOption
from py_build_cmake.config.options.override import ConfigOverrider
from py_build_cmake.config.options.string import StringConfigOption
from py_build_cmake.config.options.value_reference import (
    OverrideAction,
    OverrideActionEnum,
    ValueReference,
)
from py_build_cmake.config.options.verify import ConfigVerifier


def gen_test_opts():
    leaf11 = StringConfigOption("leaf11")
    leaf12 = StringConfigOption("leaf12")
    mid1 = ConfigOption("mid1")
    mid1.insert(leaf11)
    mid1.insert(leaf12)
    leaf21 = StringConfigOption("leaf21")
    leaf22 = StringConfigOption("leaf22")
    mid2 = ConfigOption("mid2")
    mid2.insert(leaf21)
    mid2.insert(leaf22)
    trunk = ConfigOption("trunk")
    trunk.insert(mid1)
    trunk.insert(mid2)
    opts = ConfigOption("root")
    opts.insert(trunk)
    return opts


def test_update_defaults():
    opts = gen_test_opts()
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    trunk = root_ref.sub_ref(ConfPath.from_string("trunk"))
    assert trunk.config.name == "trunk"
    mid1 = root_ref.sub_ref(ConfPath.from_string("trunk/mid1"))
    assert mid1.config.name == "mid1"
    leaf12 = root_ref.sub_ref(ConfPath.from_string("trunk/mid1/leaf12"))
    assert leaf12.config.name == "leaf12"

    values = {}
    rval = ValueReference(ConfPath.from_string("/"), values)
    trunk.config.default = DefaultValueValue({})
    rval.values = ConfigFinalizer(root=root_ref, ref=root_ref, values=rval).finalize()
    ConfigDefaulter(root=root_ref, root_values=rval).update_default()
    assert rval.values == {"trunk": {}}

    values = {}
    rval = ValueReference(ConfPath.from_string("/"), values)
    leaf12.config.default = DefaultValueValue("d12")
    rval.values = ConfigFinalizer(root=root_ref, ref=root_ref, values=rval).finalize()
    ConfigDefaulter(root=root_ref, root_values=rval).update_default()
    assert rval.values == {"trunk": {}}

    values = {}
    rval = ValueReference(ConfPath.from_string("/"), values)
    mid1.config.default = DefaultValueValue({})
    rval.values = ConfigFinalizer(root=root_ref, ref=root_ref, values=rval).finalize()
    ConfigDefaulter(root=root_ref, root_values=rval).update_default()
    assert rval.values == {"trunk": {"mid1": {"leaf12": "d12"}}}

    values = {}
    rval = ValueReference(ConfPath.from_string("/"), values)
    trunk.config.default = NoDefaultValue()
    rval.values = ConfigFinalizer(root=root_ref, ref=root_ref, values=rval).finalize()
    ConfigDefaulter(root=root_ref, root_values=rval).update_default()
    assert rval.values == {}


def test_override0():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
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
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }


def test_override1():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }
    override_values = {"leaf21": "23"}
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    override_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref.sub_ref(ConfPath.from_string("trunk/mid2")),
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref.sub_ref(ConfPath.from_string("trunk/mid2")),
        values=rval.sub_ref(ConfPath.from_string("trunk/mid2")),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref.sub_ref(ConfPath.from_string("trunk/mid2")),
        values=ValueReference(ConfPath.from_string("trunk/mid2"), overridden_values),
    ).finalize()

    assert finalized_values == {
        "leaf21": "23",
        "leaf22": "22",
    }


def test_override2():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }
    override_values = {
        "leaf21": "31",
        "leaf22": "32",
    }
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    override_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref.sub_ref(ConfPath.from_string("trunk/mid2")),
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref.sub_ref(ConfPath.from_string("trunk/mid2")),
        values=rval.sub_ref(ConfPath.from_string("trunk/mid2")),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref.sub_ref(ConfPath.from_string("trunk/mid2")),
        values=ValueReference(ConfPath.from_string("trunk/mid2"), overridden_values),
    ).finalize()

    assert finalized_values == {
        "leaf21": "31",
        "leaf22": "32",
    }


def test_override_action():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }
    override_values = {
        "trunk": {
            "mid1": {
                "leaf11": OverrideAction(OverrideActionEnum.Clear, None),
                "leaf12": OverrideAction(OverrideActionEnum.Append, "34"),
            },
            "mid2": {
                "leaf21": OverrideAction(OverrideActionEnum.Remove, "2"),
                "leaf22": OverrideAction(OverrideActionEnum.Assign, "99"),
            },
        },
    }
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
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
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/"), overridden_values),
    ).finalize()

    assert finalized_values == {
        "trunk": {
            "mid1": {
                "leaf12": "1234",
            },
            "mid2": {
                "leaf21": "1",
                "leaf22": "99",
            },
        },
    }


def test_override_override_action_append_prepend_remove():
    trunk = ConfigOption("trunk")
    trunk.insert_multiple(
        [
            StringConfigOption("str"),
            ListOfStrConfigOption("list"),
            DictOfStrConfigOption("dict"),
        ]
    )
    opts = ConfigOption("root")
    opts.insert(trunk)
    values = {
        "trunk": {
            "str": "abcdef",
            "list": ["abc", "def"],
            "dict": {"x": "abcdef"},
        },
    }
    override_values = [
        {
            "trunk": {
                "str": OverrideAction(OverrideActionEnum.Append, "ghi"),
                "list": OverrideAction(OverrideActionEnum.Append, ["ghi"]),
                "dict": {"x": OverrideAction(OverrideActionEnum.Append, "ghi")},
            }
        },
        {
            "trunk": {
                "str": OverrideAction(OverrideActionEnum.Prepend, "xyz"),
                "list": OverrideAction(OverrideActionEnum.Prepend, ["xyz"]),
                "dict": {"x": OverrideAction(OverrideActionEnum.Prepend, "xyz")},
            }
        },
        {
            "trunk": {
                "str": OverrideAction(OverrideActionEnum.Remove, "def"),
                "list": OverrideAction(OverrideActionEnum.Remove, ["def"]),
                "dict": {"x": OverrideAction(OverrideActionEnum.Remove, "def")},
            }
        },
    ]
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    for ovr in override_values:
        verified = ConfigVerifier(
            root=root_ref,
            ref=root_ref,
            values=ValueReference(ConfPath.from_string("/override"), ovr),
        ).verify()
        rval.values = ConfigOverrider(
            root=root_ref,
            ref=root_ref,
            values=rval,
            new_values=ValueReference(ConfPath.from_string("/override"), verified),
        ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).finalize()

    assert finalized_values == {
        "trunk": {
            "str": "xyzabcghi",
            "list": ["xyz", "abc", "ghi"],
            "dict": {"x": "xyzabcghi"},
        },
    }


def test_override_trunk():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }
    override_values = {
        "mid1": {
            "leaf12": "33",
        },
        "mid2": {
            "leaf21": "31",
            "leaf22": "32",
        },
    }
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    override_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref.sub_ref("trunk"),
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref.sub_ref("trunk"),
        values=rval.sub_ref("trunk"),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref.sub_ref("trunk"),
        values=ValueReference(ConfPath.from_string("/override"), overridden_values),
    ).finalize()

    assert finalized_values == {
        "mid1": {
            "leaf11": "11",
            "leaf12": "33",
        },
        "mid2": {
            "leaf21": "31",
            "leaf22": "32",
        },
    }


def test_override_root():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }
    override_values = {
        "trunk": {
            "mid1": {
                "leaf12": "33",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": "32",
            },
        }
    }
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    override_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=rval,
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), overridden_values),
    ).finalize()

    assert finalized_values == {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "33",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": "32",
            },
        }
    }


def test_override_root_verify():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }
    override_values = {
        "trunk": {
            "mid1": {
                "leaf12": "33",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": "32",
            },
        }
    }
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=rval,
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), overridden_values),
    ).finalize()

    assert finalized_values == {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "33",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": "32",
            },
        }
    }


def test_override_root_verify_unknown_option():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }
    override_values = {
        "trunk": {
            "mid1": {
                "leaf12": "33",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": "32",
                "leaf23": "32",
            },
        }
    }
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    with pytest.raises(
        ConfigError,
        match="^Unknown option 'leaf23' in override/trunk/mid2. Did you mean: leaf22, leaf21$",
    ):
        ConfigVerifier(
            root=root_ref,
            ref=root_ref,
            values=ValueReference(ConfPath.from_string("/override"), override_values),
        ).verify()


def test_override_root_verify_wrong_type():
    opts = gen_test_opts()
    values = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }
    override_values = {
        "trunk": {
            "mid1": {
                "leaf12": "33",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": 32,
            },
        }
    }
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    with pytest.raises(
        ConfigError,
        match="^Type of override/trunk/mid2/leaf22 should be <class 'str'>, not <class 'int'>$",
    ):
        ConfigVerifier(
            root=root_ref,
            ref=root_ref,
            values=ValueReference(ConfPath.from_string("/override"), override_values),
        ).verify()


def test_override_append_prepend_assign():
    opts = ConfigOption("root")
    trunk = ConfigOption("trunk")
    subopt = ConfigOption("subopt")
    subopt.insert_multiple(
        [
            ListOfStrConfigOption("args0a", append_by_default=True),
            ListOfStrConfigOption("args1a"),
            ListOfStrConfigOption("args1b"),
            ListOfStrConfigOption("args1c"),
            ListOfStrConfigOption("args2a"),
            ListOfStrConfigOption("args2b"),
            ListOfStrConfigOption("args3a"),
            ListOfStrConfigOption("args3b"),
            ListOfStrConfigOption("args3c"),
        ]
    )
    trunk.insert(subopt)
    opts.insert(trunk)

    values = {
        "trunk": {
            "subopt": {
                "args0a": ["abc", "def", "ghi"],
                "args1a": ["abc", "def", "ghi"],
                "args1b": ["abc", "def", "ghi"],
                "args1c": ["abc", "def", "ghi"],
                "args2a": [],
                "args2b": [],
            },
        },
    }
    override_values = {
        "subopt": {
            "args0a": ["123"],
            "args1a": ["123"],
            "args1b": {"=": ["456"]},
            "args1c": {"-": ["def", "xyz"], "+": ["jkl"], "prepend": ["000"]},
            "args2a": {"+": ["789"]},
            "args2b": {"=": ["321"]},
            "args3a": {"+": ["654"]},
            "args3b": {"=": ["987"]},
            "args3c": {"-": ["foo"]},
        },
    }
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    override_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref.sub_ref("trunk"),
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref.sub_ref("trunk"),
        values=rval.sub_ref("trunk"),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref.sub_ref("trunk"),
        values=ValueReference(ConfPath.from_string("/override"), overridden_values),
    ).finalize()

    assert finalized_values == {
        "subopt": {
            "args0a": ["abc", "def", "ghi", "123"],
            "args1a": ["123"],
            "args1b": ["456"],
            "args1c": ["000", "abc", "ghi", "jkl"],
            "args2a": ["789"],
            "args2b": ["321"],
            "args3a": ["654"],
            "args3b": ["987"],
            "args3c": [],
        },
    }


class ConfigTestOption(ConfigOption):
    def override(self, old_value, new_value):
        if old_value.values is None:
            return new_value.values
        assert isinstance(old_value.values, str)
        assert isinstance(new_value.values, str)
        return old_value.values + "+" + new_value.values

    def verify(self, values: ValueReference) -> Any:
        assert isinstance(values.values, str)
        return values.values


def test_override_no_inherit():
    root = ConfigOption("")
    a = root.sub_options["a"] = ConfigOption("a")
    a.sub_options["1"] = ConfigTestOption("1")
    a.sub_options["2"] = ConfigTestOption("2")
    a.sub_options["3"] = ConfigTestOption("3")
    b = root.sub_options["b"] = ConfigOption("b")
    b.sub_options["1"] = ConfigTestOption("1")

    values = {"a": {"1": "a1", "2": "a2"}}
    override_values = {"a": {"2": "A2", "3": "A3"}, "b": {"1": "B1"}}

    root_ref = ConfigReference(ConfPath.from_string("/"), root)
    rval = ValueReference(ConfPath.from_string("/"), values)
    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    override_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=rval,
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), overridden_values),
    ).finalize()

    pprint(finalized_values)
    assert finalized_values == {
        "a": {"1": "a1", "2": "a2+A2", "3": "A3"},
        "b": {"1": "B1"},
    }


def test_override_inherit():
    root = ConfigOption("")
    a = root.sub_options["a"] = ConfigOption("a")
    a.sub_options["1"] = ConfigTestOption("1")
    a.sub_options["2"] = ConfigTestOption("2")
    a.sub_options["3"] = ConfigTestOption("3")
    b = root.sub_options["b"] = ConfigOption("b")
    b.sub_options["1"] = ConfigTestOption("1")
    c = root.sub_options["c"] = ConfigOption("c")
    c.inherits = ConfPath.from_string("/a")
    d = root.sub_options["d"] = ConfigOption("d")
    d.inherits = ConfPath.from_string("/a/1")
    e = root.sub_options["e"] = ConfigOption("e")
    e.inherits = ConfPath.from_string("/c")

    values = {"a": {"1": "a1", "2": "a2"}}
    override_values = {
        "a": {"2": "A2", "3": "A3"},
        "b": {"1": "B1"},
        "c": {"1": "C1"},
        "d": "D",
        "e": {"3": "E3"},
    }

    root_ref = ConfigReference(ConfPath.from_string("/"), root)
    rval = ValueReference(ConfPath.from_string("/"), values)
    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    override_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=rval,
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/override"), overridden_values),
    ).finalize()

    pprint(finalized_values)
    assert finalized_values == {
        "a": {"1": "a1", "2": "a2+A2", "3": "A3"},
        "b": {"1": "B1"},
        "c": {"1": "C1"},
        "d": "D",
        "e": {"3": "E3"},
    }


def test_override_action_inherit():
    a = ConfigOption("a")
    a.insert_multiple(
        [
            StringConfigOption("str_append_clear"),
            StringConfigOption("str_clear_append"),
            StringConfigOption("str_append_remove_1"),
            StringConfigOption("str_append_remove_2"),
            StringConfigOption("str_remove_append_1"),
            StringConfigOption("str_remove_append_2"),
        ]
    )
    b = ConfigOption("b")
    b.inherits = ConfPath.from_string("/a")
    opts = ConfigOption("")
    opts.insert_multiple([a, b])

    values = {
        "a": {
            "str_append_clear": "abcdef",
            "str_clear_append": "abcdef",
            "str_append_remove_1": "abcdef",
            "str_append_remove_2": "abcdef",
            "str_remove_append_1": "abcdef",
            "str_remove_append_2": "abcdef",
        },
        "b": {
            "str_append_clear": OverrideAction(OverrideActionEnum.Append, "ghi"),
            "str_clear_append": OverrideAction(OverrideActionEnum.Clear, None),
            "str_append_remove_1": OverrideAction(OverrideActionEnum.Append, "ghi"),
            "str_append_remove_2": OverrideAction(OverrideActionEnum.Append, "ghi"),
            "str_remove_append_1": OverrideAction(OverrideActionEnum.Remove, "de"),
            "str_remove_append_2": OverrideAction(OverrideActionEnum.Remove, "gh"),
        },
    }
    override_values = [
        {
            "b": {
                "str_append_clear": OverrideAction(OverrideActionEnum.Clear, None),
                "str_clear_append": OverrideAction(OverrideActionEnum.Append, "ghi"),
                "str_append_remove_1": OverrideAction(OverrideActionEnum.Remove, "de"),
                "str_append_remove_2": OverrideAction(OverrideActionEnum.Remove, "gh"),
                "str_remove_append_1": OverrideAction(OverrideActionEnum.Append, "ghi"),
                "str_remove_append_2": OverrideAction(OverrideActionEnum.Append, "ghi"),
            }
        }
    ]
    root_ref = ConfigReference(ConfPath.from_string("/"), opts)
    rval = ValueReference(ConfPath.from_string("/"), values)

    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    for ovr in override_values:
        verified = ConfigVerifier(
            root=root_ref,
            ref=root_ref,
            values=ValueReference(ConfPath.from_string("/override"), ovr),
        ).verify()
        rval.values = ConfigOverrider(
            root=root_ref,
            ref=root_ref,
            values=rval,
            new_values=ValueReference(ConfPath.from_string("/override"), verified),
        ).override()
    ConfigInheritor(
        root=root_ref,
        root_values=rval,
    ).inherit()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).finalize()

    pprint(finalized_values)
    assert finalized_values == {
        "a": {
            "str_append_clear": "abcdef",
            "str_clear_append": "abcdef",
            "str_append_remove_1": "abcdef",
            "str_append_remove_2": "abcdef",
            "str_remove_append_1": "abcdef",
            "str_remove_append_2": "abcdef",
        },
        "b": {
            # "str_append_clear": <unset>,
            "str_clear_append": "ghi",
            "str_append_remove_1": "abcfghi",
            "str_append_remove_2": "abcdefi",
            "str_remove_append_1": "abcfghi",
            "str_remove_append_2": "abcdefghi",
        },
    }


def test_inherit():
    root = ConfigOption("")
    a = root.sub_options["a"] = ConfigOption("a")
    a.sub_options["1"] = ConfigTestOption("1")
    a.sub_options["2"] = ConfigTestOption("2")
    a.sub_options["3"] = ConfigTestOption("3")
    b = root.sub_options["b"] = ConfigOption("b")
    b.sub_options["1"] = ConfigTestOption("1")
    c = root.sub_options["c"] = ConfigOption("c")
    c.inherits = ConfPath.from_string("/a")
    c.create_if_inheritance_target_exists = True
    d = root.sub_options["d"] = ConfigOption("d")
    d.inherits = ConfPath.from_string("/a/1")
    d.create_if_inheritance_target_exists = True
    e = root.sub_options["e"] = ConfigOption("e")
    e.inherits = ConfPath.from_string("/c")
    e.create_if_inheritance_target_exists = True

    values = {
        "a": {"1": "a1", "2": "a2"},
        "b": {"1": "B1"},
        "c": {"1": "C1"},
        "d": "D1",
        "e": {"1": "E1", "2": "E2", "3": "E3"},
    }

    root_ref = ConfigReference(ConfPath.from_string("/"), root)
    rval = ValueReference(ConfPath.from_string("/"), values)
    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    ConfigInheritor(
        root=root_ref,
        root_values=rval,
    ).inherit()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).finalize()

    print(finalized_values)
    assert finalized_values == {
        "a": {"1": "a1", "2": "a2"},
        "b": {"1": "B1"},
        "c": {"1": "a1+C1", "2": "a2"},
        "d": "a1+D1",
        "e": {"1": "a1+C1+E1", "2": "a2+E2", "3": "E3"},
    }


class VerifiedConfigOption(ConfigOption):
    def __init__(self, name, verified: set) -> None:
        super().__init__(name)
        self.verified = verified

    def verify(self, values: ValueReference):
        self.verified.add(values.value_path.pth)
        return values.values


def test_verify():
    verified = set()
    root = ConfigOption("")
    a = root.sub_options["a"] = ConfigOption("a")
    a.sub_options["1"] = VerifiedConfigOption("1", verified)
    a.sub_options["2"] = VerifiedConfigOption("2", verified)
    a.sub_options["3"] = VerifiedConfigOption("3", verified)
    b = root.sub_options["b"] = ConfigOption("b")
    b.sub_options["1"] = VerifiedConfigOption("1", verified)
    c = root.sub_options["c"] = ConfigOption("c")
    c.inherits = ConfPath.from_string("/a")
    c.create_if_inheritance_target_exists = True
    d = root.sub_options["d"] = ConfigOption("d")
    d.inherits = ConfPath.from_string("/a/1")
    d.create_if_inheritance_target_exists = True
    e = root.sub_options["e"] = ConfigOption("e")
    e.inherits = ConfPath.from_string("/c")
    e.create_if_inheritance_target_exists = True

    values = {
        "a": {"1": "a1", "2": "a2"},
        "b": {"1": "B1"},
        "c": {"1": "C1"},
        "d": "D1",
        "e": {"1": "E1", "2": "E2", "3": "E3"},
    }

    root_ref = ConfigReference(ConfPath.from_string("/"), root)
    rval = ValueReference(ConfPath.from_string("/"), values)
    verified_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    finalized_values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/"), verified_values),
    ).finalize()

    print(finalized_values)
    assert finalized_values == values
    assert verified == {
        ConfPath.from_string("a/1").pth,
        ConfPath.from_string("a/2").pth,
        ConfPath.from_string("b/1").pth,
        ConfPath.from_string("c/1").pth,
        ConfPath.from_string("d").pth,
        ConfPath.from_string("e/1").pth,
        ConfPath.from_string("e/2").pth,
        ConfPath.from_string("e/3").pth,
    }


def test_default():
    root = ConfigOption("")
    root.insert_multiple(
        [
            # Default value
            ConfigTestOption("a", default=DefaultValueValue("foo")),
            # Refer to other (existing) value
            ConfigTestOption(
                "b", default=RefDefaultValue(ConfPath.from_string("a"), relative=True)
            ),
            ConfigTestOption(
                "c", default=RefDefaultValue(ConfPath.from_string("a"), relative=False)
            ),
            ConfigTestOption(
                "d", default=RefDefaultValue(ConfPath.from_string("b"), relative=False)
            ),
            ConfigTestOption(
                "e", default=RefDefaultValue(ConfPath.from_string("c"), relative=False)
            ),
            # Refer to other (existing) value, but it already has a value
            ConfigTestOption(
                "f", default=RefDefaultValue(ConfPath.from_string("a"), relative=True)
            ),
            ConfigTestOption(
                "g", default=RefDefaultValue(ConfPath.from_string("f"), relative=True)
            ),
            ConfigTestOption(
                "h", default=RefDefaultValue(ConfPath.from_string("g"), relative=True)
            ),
            # No default value (should not create any values)
            ConfigTestOption("i"),
            ConfigTestOption("j", default=NoDefaultValue()),
            ConfigTestOption("k", default=NoDefaultValue()),
            # Refer to another (unset) value
            ConfigTestOption("l", default=RefDefaultValue(ConfPath.from_string("k"))),
            ConfigTestOption("r", default=RequiredValue()),
            ConfigOption("s", default=DefaultValueValue({})).insert_multiple(
                [
                    ConfigTestOption("1", default=DefaultValueValue("s1d")),
                    ConfigTestOption(
                        "2", default=RefDefaultValue(ConfPath.from_string("g"))
                    ),
                    ConfigTestOption("3", default=NoDefaultValue()),
                    ConfigTestOption(
                        "4",
                        default=RefDefaultValue(
                            ConfPath.from_string("2"), relative=True
                        ),
                    ),
                ]
            ),
        ]
    )
    values = {"f": "bar", "j": "zzz", "r": "baz"}

    root_ref = ConfigReference(ConfPath.from_string("/"), root)
    rval = ValueReference(ConfPath.from_string("/"), values)
    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    rval.values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).finalize()
    ConfigDefaulter(
        root=root_ref,
        root_values=rval,
    ).update_default()

    print(rval.values)
    assert rval.values == {
        "a": "foo",
        "b": "foo",
        "c": "foo",
        "d": "foo",
        "e": "foo",
        "f": "bar",
        "g": "bar",
        "h": "bar",
        "j": "zzz",
        "r": "baz",
        "s": {
            "1": "s1d",
            "2": "bar",
            "4": "bar",
        },
    }


def test_default_missing():
    root = ConfigOption("")
    root.insert_multiple(
        [
            ConfigTestOption("a", default=RequiredValue()),
            ConfigTestOption("mis", default=RequiredValue()),
        ]
    )
    values = {"a": "foo"}

    root_ref = ConfigReference(ConfPath.from_string("/"), root)
    rval = ValueReference(ConfPath.from_string("/"), values)
    rval.values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    rval.values = ConfigFinalizer(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).finalize()
    defaulter = ConfigDefaulter(
        root=root_ref,
        root_values=rval,
    )
    with pytest.raises(MissingDefaultError, match="^mis requires a value$"):
        defaulter.update_default()
