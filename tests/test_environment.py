import os

from py_build_cmake.config.environment import (
    StringOption,
    substitute_environment_options,
)


def test_environment_value():
    env = {"FOO": "bar"}
    env_opts = {"BAZ": StringOption(value="abc")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": "abc"}


def test_environment_value_empty_string():
    env = {"FOO": "bar"}
    env_opts = {"BAZ": StringOption(value="")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": ""}


def test_environment_value_expand():
    env = {"FOO": "bar", "DEF": "def"}
    env_opts = {"BAZ": StringOption(value="abc$DEF")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "DEF": "def", "BAZ": "abcdef"}


def test_environment_value_expand_braces():
    env = {"FOO": "bar", "DEF": "def"}
    env_opts = {"BAZ": StringOption(value="abc${DEF}ghi")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "DEF": "def", "BAZ": "abcdefghi"}


def test_environment_value_escape():
    env = {"FOO": "bar", "DEF": "def"}
    env_opts = {"BAZ": StringOption(value="abc$${DEF}")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "DEF": "def", "BAZ": "abc${DEF}"}


def test_environment_value_escape_dollar():
    env = {"FOO": "bar", "DEF": "def"}
    env_opts = {"BAZ": StringOption(value="abc$$f")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "DEF": "def", "BAZ": "abc$f"}


def test_environment_append():
    env = {"FOO": "bar", "BAZ": "abc"}
    env_opts = {"BAZ": StringOption(append="def")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": "abcdef"}


def test_environment_append_empty():
    env = {"FOO": "bar"}
    env_opts = {"BAZ": StringOption(append="def")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": "def"}


def test_environment_prepend():
    env = {"FOO": "bar", "BAZ": "abc"}
    env_opts = {"BAZ": StringOption(prepend="def")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": "defabc"}


def test_environment_prepend_empty():
    env = {"FOO": "bar"}
    env_opts = {"BAZ": StringOption(prepend="def")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": "def"}


def test_environment_append_path():
    env = {"FOO": "bar", "BAZ": "abc"}
    env_opts = {"BAZ": StringOption(append_path="def")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": "abc" + os.pathsep + "def"}


def test_environment_append_path_empty():
    env = {"FOO": "bar"}
    env_opts = {"BAZ": StringOption(append_path="def")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": "def"}


def test_environment_prepend_path():
    env = {"FOO": "bar", "BAZ": "abc"}
    env_opts = {"BAZ": StringOption(prepend_path="def")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": "def" + os.pathsep + "abc"}


def test_environment_prepend_path_empty():
    env = {"FOO": "bar"}
    env_opts = {"BAZ": StringOption(prepend_path="def")}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar", "BAZ": "def"}


def test_environment_clear():
    env = {"FOO": "bar", "BAZ": "abc"}
    env_opts = {"BAZ": StringOption(clear=True)}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar"}


def test_environment_clear_empty():
    env = {"FOO": "bar"}
    env_opts = {"BAZ": StringOption(clear=True)}
    substitute_environment_options(env, env_opts)
    assert env == {"FOO": "bar"}
