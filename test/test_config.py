from pprint import pprint

import pytest
from py_build_cmake.config import *
from flit_core.config import ConfigError


def test_config_defaults():
    opts = ConfigOptions()
    opts.add_options([
        StringConfigOption("a.b",
                           "c",
                           "help c",
                           default=ConfigOptionRef("d.e")),
        StringConfigOption("d", "e", "help e", default="42"),
    ])

    config = {"a": {"b": {"c": "1234"}}}
    opts.update_defaults(config)
    pprint(config)
    assert opts.index_with_prefix(config, ('a', 'b', 'c')) == "1234"
    assert "d" not in config

    config = {"a": {"b": {}}}
    opts.update_defaults(config)
    pprint(config)
    assert opts.index_with_prefix(config, ('a', 'b', 'c')) == "42"
    assert "d" not in config

    config = {"a": {"b": {}}, "d": {}}
    opts.update_defaults(config)
    pprint(config)
    assert opts.index_with_prefix(config, ('a', 'b', 'c')) == "42"
    assert opts.index_with_prefix(config, ('d', 'e')) == "42"

    config = {"a": {"b": {}}, "d": {"e": "43"}}
    opts.update_defaults(config)
    pprint(config)
    assert opts.index_with_prefix(config, ('a', 'b', 'c')) == "43"
    assert opts.index_with_prefix(config, ('d', 'e')) == "43"

    config = {"a": {"b": {"c": "1234"}}, "d": {"e": "43"}}
    opts.update_defaults(config)
    pprint(config)
    assert opts.index_with_prefix(config, ('a', 'b', 'c')) == "1234"
    assert opts.index_with_prefix(config, ('d', 'e')) == "43"

    config = {"a": {"b": {"c": "1234"}}, "d": {}}
    opts.update_defaults(config)
    pprint(config)
    assert opts.index_with_prefix(config, ('a', 'b', 'c')) == "1234"
    assert opts.index_with_prefix(config, ('d', 'e')) == "42"

    opts.add_option(
        StringConfigOption("d", "f", "help f", default=ConfigOption.Required))
    config = {"a": {"b": {"c": "1234"}}}
    opts.update_defaults(config)
    opts.verify(config)

    config = {"a": {"b": {"c": "1234"}}, "d": {}}
    with pytest.raises(ConfigError, match="Missing required option d.f"):
        opts.update_defaults(config)

    config = {"a": {"b": {"c": "1234"}}, "d": {"f": "ok"}}
    opts.update_defaults(config)


def test_config_verify():
    opts = ConfigOptions()
    opts.add_options([StringConfigOption("a.b", "c", "help c")])
    config = {"a": {"b": {"c": 1234}}}
    opts.update_defaults(config)
    with pytest.raises(
            ConfigError,
            match=
            "Type of field a.b.c should be <class 'str'>, not <class 'int'>"):
        opts.verify(config)


def test_config_override():
    opts = ConfigOptions()
    opts.add_options([StringConfigOption("a.b", "c", "help c")])
    config = {"a": {"b": {"c": "1"}}}
    overrideconfig = {"c": "2"}
    opts.update_defaults(config)
    opts.verify(config)
    opts.override(config, ('a', 'b'), overrideconfig)
    assert opts.index_with_prefix(config, ('a', 'b', 'c')) == "2"

    opts = ConfigOptions()
    opts.add_options([ListOfStringOption("a.b", "c", "help c")])
    config = {"a": {"b": {"c": ["1"]}}}
    overrideconfig = {"c": ["2"]}
    opts.update_defaults(config)
    opts.verify(config)
    opts.override(config, ('a', 'b'), overrideconfig)
    assert opts.index_with_prefix(config, ('a', 'b', 'c')) == ["1", "2"]

    opts = ConfigOptions()
    opts.add_options([DictOfStringOption("a.b", "c", "help c")])
    config = {"a": {"b": {"c": {"1": "a", "2": "b"}}}}
    overrideconfig = {"c": {"2": "B", "3": "C"}}
    opts.update_defaults(config)
    opts.verify(config)
    opts.override(config, ('a', 'b'), overrideconfig)
    assert opts.index_with_prefix(config, ('a', 'b', 'c')) == {
        "1": "a",
        "2": "B",
        "3": "C",
    }
