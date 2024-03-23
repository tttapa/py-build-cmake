from pprint import pprint

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
from py_build_cmake.config.options.inherit import ConfigInheritor
from py_build_cmake.config.options.list import ListOfStrConfigOption
from py_build_cmake.config.options.override import ConfigOverrider
from py_build_cmake.config.options.string import StringConfigOption
from py_build_cmake.config.options.value_reference import ValueReference
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
    ConfigDefaulter(root=root_ref, root_values=rval).update_default()
    assert values == {"trunk": {}}

    values = {}
    rval = ValueReference(ConfPath.from_string("/"), values)
    leaf12.config.default = DefaultValueValue("d12")
    ConfigDefaulter(root=root_ref, root_values=rval).update_default()
    assert values == {"trunk": {}}

    values = {}
    rval = ValueReference(ConfPath.from_string("/"), values)
    mid1.config.default = DefaultValueValue({})
    ConfigDefaulter(root=root_ref, root_values=rval).update_default()
    assert values == {"trunk": {"mid1": {"leaf12": "d12"}}}

    values = {}
    rval = ValueReference(ConfPath.from_string("/"), values)
    trunk.config.default = NoDefaultValue()
    ConfigDefaulter(root=root_ref, root_values=rval).update_default()
    assert values == {}


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

    ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=rval,
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()

    assert overridden_values == {
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

    ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref.sub_ref(ConfPath.from_string("trunk/mid2")),
        values=rval.sub_ref(ConfPath.from_string("trunk/mid2")),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()

    assert overridden_values == {
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

    ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref.sub_ref(ConfPath.from_string("trunk/mid2")),
        values=rval.sub_ref(ConfPath.from_string("trunk/mid2")),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()

    assert overridden_values == {
        "leaf21": "31",
        "leaf22": "32",
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

    ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref.sub_ref("trunk"),
        values=rval.sub_ref("trunk"),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()

    assert overridden_values == {
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

    ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=rval,
    ).verify()
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=rval,
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()

    assert overridden_values == {
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

    assert overridden_values == {
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

    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref.sub_ref("trunk"),
        values=rval.sub_ref("trunk"),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()

    assert overridden_values == {
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
        if new_value.values is None:
            return old_value.values
        if old_value.values is None:
            return new_value.values
        return old_value.values + "+" + new_value.values


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
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/"), values),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()

    print(overridden_values)
    assert overridden_values == {
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
    overridden_values = ConfigOverrider(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/"), values),
        new_values=ValueReference(ConfPath.from_string("/override"), override_values),
    ).override()

    print(overridden_values)
    assert overridden_values == {
        "a": {"1": "a1", "2": "a2+A2", "3": "A3"},
        "b": {"1": "B1"},
        "c": {"1": "C1"},
        "d": "D",
        "e": {"3": "E3"},
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
    ConfigInheritor(
        root=root_ref,
        root_values=ValueReference(ConfPath.from_string("/"), values),
    ).inherit()
    inherited_values = values
    pprint(inherited_values)
    assert inherited_values == {
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
    verified_values = ConfigVerifier(
        root=root_ref,
        ref=root_ref,
        values=ValueReference(ConfPath.from_string("/"), values),
    ).verify()

    assert verified_values == values
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
    ConfigDefaulter(
        root=root_ref,
        root_values=ValueReference(ConfPath.from_string("/"), values),
    ).update_default()

    print(values)
    assert values == {
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
    defaulter = ConfigDefaulter(
        root=root_ref,
        root_values=ValueReference(ConfPath.from_string("/"), values),
    )
    with pytest.raises(MissingDefaultError, match="^mis requires a value$"):
        defaulter.update_default()
