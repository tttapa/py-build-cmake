import os
from pathlib import Path
from pprint import pprint

import pytest
import py_build_cmake.config.config_options as co
from py_build_cmake.config.pyproject_options import get_options
from py_build_cmake.common import ConfigError


def gen_test_opts():
    leaf11 = co.StrConfigOption("leaf11")
    leaf12 = co.StrConfigOption("leaf12")
    mid1 = co.ConfigOption("mid1")
    mid1.insert(leaf11)
    mid1.insert(leaf12)
    leaf21 = co.StrConfigOption("leaf21")
    leaf22 = co.StrConfigOption("leaf22")
    mid2 = co.ConfigOption("mid2")
    mid2.insert(leaf21)
    mid2.insert(leaf22)
    trunk = co.ConfigOption("trunk")
    trunk.insert(mid1)
    trunk.insert(mid2)
    opts = co.ConfigOption("root")
    opts.insert(trunk)
    return opts


def test_iter():
    opts = gen_test_opts()
    result = [p for p in opts.iter_opt_paths()]
    expected = [
        ("trunk",),
        ("trunk", "mid1"),
        ("trunk", "mid1", "leaf11"),
        ("trunk", "mid1", "leaf12"),
        ("trunk", "mid2"),
        ("trunk", "mid2", "leaf21"),
        ("trunk", "mid2", "leaf22"),
    ]
    print(result)
    assert result == expected


def test_iter_leaf():
    opts = gen_test_opts()
    result = [p for p in opts.iter_leaf_opt_paths()]
    expected = [
        ("trunk", "mid1", "leaf11"),
        ("trunk", "mid1", "leaf12"),
        ("trunk", "mid2", "leaf21"),
        ("trunk", "mid2", "leaf22"),
    ]
    print(result)
    assert result == expected


def test_update_defaults():
    opts = gen_test_opts()
    trunk = opts[co.pth("trunk")]
    assert trunk.name == "trunk"
    mid1 = opts[co.pth("trunk/mid1")]
    assert mid1.name == "mid1"
    leaf12 = opts[co.pth("trunk/mid1/leaf12")]
    assert leaf12.name == "leaf12"

    cfg = co.ConfigNode.from_dict({})
    trunk.default = co.DefaultValueValue({})
    res = trunk.update_default(opts, cfg, co.pth("trunk"))
    assert res is not None and res.value == {}
    assert cfg.to_dict() == {"trunk": {}}
    opts.update_default_all(cfg)
    assert cfg.to_dict() == {"trunk": {}}

    cfg = co.ConfigNode.from_dict({})
    leaf12.default = co.DefaultValueValue("d12")
    res = leaf12.update_default(opts, cfg, co.pth("trunk/mid1/leaf12"))
    assert res is not None and res.value == "d12"
    assert cfg.to_dict() == {}
    opts.update_default_all(cfg)
    assert cfg.to_dict() == {"trunk": {}}

    cfg = co.ConfigNode.from_dict({})
    mid1.default = co.DefaultValueValue({})
    res = leaf12.update_default(opts, cfg, co.pth("trunk/mid1/leaf12"))
    assert res is not None and res.value == "d12"
    assert cfg.to_dict() == {}
    opts.update_default_all(cfg)
    assert cfg.to_dict() == {"trunk": {"mid1": {"leaf12": "d12"}}}

    cfg = co.ConfigNode.from_dict({})
    print(cfg)
    print(cfg.value)
    print(cfg.sub)
    trunk.default = co.NoDefaultValue()
    res = leaf12.update_default(opts, cfg, co.pth("trunk/mid1/leaf12"))
    assert res is not None and res.value == "d12"
    assert cfg.to_dict() == {}
    print(cfg)
    print(cfg.value)
    print(cfg.sub)
    opts.update_default_all(cfg)
    assert cfg.to_dict() == {}


def test_override0():
    opts = gen_test_opts()
    d = {
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
        # No override
    }
    opts[co.pth("")].insert(
        co.OverrideConfigOption(
            "override_mid2",
            "",
            targetpath=co.pth("trunk/mid2"),
        )
    )
    cfg = co.ConfigNode.from_dict(d)
    opts.verify_all(cfg)
    opts.override_all(cfg)
    assert cfg.to_dict() == {
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
    d = {
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
        "override_mid2": {"leaf21": "23"},
    }
    opts[co.pth("")].insert(
        co.OverrideConfigOption(
            "override_mid2",
            "",
            targetpath=co.pth("trunk/mid2"),
        )
    )
    cfg = co.ConfigNode.from_dict(d)
    opts.verify_all(cfg)
    opts.override_all(cfg)
    assert cfg.to_dict() == {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "23",
                "leaf22": "22",
            },
        },
        "override_mid2": {"leaf21": "23"},
    }


def test_override2():
    opts = gen_test_opts()
    d = {
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
        "override_mid2": {
            "leaf21": "31",
            "leaf22": "32",
        },
    }
    opts[co.pth("")].insert(
        co.OverrideConfigOption(
            "override_mid2",
            "",
            targetpath=co.pth("trunk/mid2"),
        )
    )
    cfg = co.ConfigNode.from_dict(d)
    opts.verify_all(cfg)
    opts.override_all(cfg)
    assert cfg.to_dict() == {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": "32",
            },
        },
        "override_mid2": {
            "leaf21": "31",
            "leaf22": "32",
        },
    }


def test_override_trunk():
    opts = gen_test_opts()
    d = {
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
        "override_trunk": {
            "mid1": {
                "leaf12": "33",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": "32",
            },
        },
    }
    opts[co.pth("")].insert(
        co.OverrideConfigOption(
            "override_trunk",
            "",
            targetpath=co.pth("trunk"),
        )
    )
    cfg = co.ConfigNode.from_dict(d)
    opts.verify_all(cfg)
    opts.override_all(cfg)
    assert cfg.to_dict() == {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "33",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": "32",
            },
        },
        "override_trunk": {
            "mid1": {
                "leaf12": "33",
            },
            "mid2": {
                "leaf21": "31",
                "leaf22": "32",
            },
        },
    }


def test_verify_override_unknown_keys():
    opts = gen_test_opts()
    d = {
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
        "override_mid2": {
            "blahblah": "31",
            "leaf22": "32",
        },
    }
    opts[co.pth("")].insert(
        co.OverrideConfigOption(
            "override_mid2",
            "",
            targetpath=co.pth("trunk/mid2"),
        )
    )
    cfg = co.ConfigNode.from_dict(d)
    expected = "Unknown options in override_mid2: blahblah"
    with pytest.raises(ConfigError, match=expected) as e:
        opts.verify_all(cfg)
    print(e)


def test_override_trunk_unknown_keys():
    opts = gen_test_opts()
    d = {
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
        "override_trunk": {
            "mid1": {
                "azertyop": "33",
            },
        },
    }
    opts[co.pth("")].insert(
        co.OverrideConfigOption(
            "override_trunk",
            "",
            targetpath=co.pth("trunk"),
        )
    )
    cfg = co.ConfigNode.from_dict(d)
    expected = "Unknown options in override_trunk/mid1: azertyop"
    with pytest.raises(ConfigError, match=expected) as e:
        opts.verify_all(cfg)
    print(e)


def test_verify_unknown_keys1():
    opts = gen_test_opts()
    d = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
            "mid3": "foobar",
        },
    }
    cfg = co.ConfigNode.from_dict(d)
    expected = "Unknown options in trunk: mid3"
    with pytest.raises(ConfigError, match=expected) as e:
        opts.verify_all(cfg)
    print(e)


def test_verify_unknown_keys2():
    opts = gen_test_opts()
    d = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
                "foobar": 1234,
            },
        },
    }
    cfg = co.ConfigNode.from_dict(d)
    expected = "Unknown options in trunk/mid2: foobar"
    with pytest.raises(ConfigError, match=expected) as e:
        opts.verify_all(cfg)
    print(e)


def test_verify_wrong_type_str():
    opts = gen_test_opts()
    d = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": 1234,
            },
        },
    }
    cfg = co.ConfigNode.from_dict(d)
    expected = "Type of trunk/mid2/leaf22 should be <class 'str'>, " "not <class 'int'>"
    with pytest.raises(ConfigError, match=expected) as e:
        opts.verify_all(cfg)
    print(e)


def test_verify_wrong_type_str_dict():
    opts = gen_test_opts()
    d = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": {"21": 1234},
            },
        },
    }
    cfg = co.ConfigNode.from_dict(d)
    expected = (
        "Type of trunk/mid2/leaf21 should be <class 'str'>, " "not <class 'dict'>"
    )
    with pytest.raises(ConfigError, match=expected) as e:
        opts.verify_all(cfg)
    print(e)


def test_inherit():
    opts = gen_test_opts()
    d = {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
            "mid3": {},
        },
    }
    mid3 = opts[co.pth("trunk")].insert(
        co.ConfigOption("mid3", inherit_from=co.pth("trunk/mid2"))
    )

    cfg = co.ConfigNode.from_dict(d)
    mid3.inherit(opts, cfg, co.pth("trunk/mid3"))
    assert cfg.to_dict() == {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
            "mid3": {
                "leaf21": "21",
                "leaf22": "22",
            },
        },
    }

    cfg = co.ConfigNode.from_dict(d)
    cfg.setdefault(co.pth("trunk/mid3/leaf22"), co.ConfigNode(value="32"))
    mid3.inherit(opts, cfg, co.pth("trunk/mid3"))
    assert cfg.to_dict() == {
        "trunk": {
            "mid1": {
                "leaf11": "11",
                "leaf12": "12",
            },
            "mid2": {
                "leaf21": "21",
                "leaf22": "22",
            },
            "mid3": {
                "leaf21": "21",
                "leaf22": "32",
            },
        },
    }


def test_config_node():
    d = {
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
    nodes = co.ConfigNode.from_dict(d)
    for pth, val in nodes.iter_dfs():
        print(pth, val.value)
    assert nodes[co.pth("")] is nodes
    assert nodes[co.pth("")].value is None
    assert nodes[co.pth("trunk")].value is None
    assert nodes[co.pth("trunk/mid1")].value is None
    assert nodes[co.pth("trunk/mid2")].value is None
    assert nodes[co.pth("trunk/mid1/leaf11")].value == "11"
    assert nodes[co.pth("trunk/mid1/leaf12")].value == "12"
    assert nodes[co.pth("trunk/mid2/leaf21")].value == "21"
    assert nodes[co.pth("trunk/mid2/leaf22")].value == "22"

    d2 = nodes.to_dict()
    assert d2 == d


def test_joinpth():
    assert co.joinpth(co.pth("a/b/c"), co.pth("d/e")) == co.pth("a/b/c/d/e")
    assert co.joinpth(co.pth("a/b/c"), co.pth("^/e")) == co.pth("a/b/e")
    assert co.joinpth(co.pth("a/b/c"), co.pth("^/^/e")) == co.pth("a/e")
    assert co.joinpth(co.pth("a/b/c"), co.pth("^/^/^/e")) == co.pth("e")
    assert co.joinpth(co.pth("a/b/c"), co.pth("^/^/^/^/e")) == co.pth("^/e")


def test_real_config_inherit_cross_cmake():
    opts = get_options(Path("/project"), test=True)
    d = {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {
                "some-other-tool": {},
                "py-build-cmake": {
                    "cmake": {
                        "build_type": "Release",
                        "generator": "Ninja",
                        "source_path": "src",
                        "env": {"foo": "bar"},
                        "args": ["arg1", "arg2"],
                        "find_python": False,
                        "find_python3": True,
                    },
                    "cross": {
                        "implementation": "cp",
                        "version": "310",
                        "abi": "cp310",
                        "arch": "linux_aarch64",
                        "toolchain_file": "aarch64-linux-gnu.cmake",
                        "cmake": {
                            "generator": "Unix Makefiles",
                            "build_type": "RelWithDebInfo",
                            "env": {"crosscompiling": "true"},
                            "args": ["arg3", "arg4"],
                        },
                    },
                    "linux": {
                        "cmake": {
                            "install_components": ["linux_install"],
                        }
                    },
                    "windows": {
                        "cmake": {
                            "install_components": ["win_install"],
                        }
                    },
                },
            },
        }
    }
    cfg = co.ConfigNode.from_dict(d)
    opts.verify_all(cfg)
    pprint(cfg.to_dict())
    opts.inherit_all(cfg)
    pprint(cfg.to_dict())
    assert cfg.to_dict() == {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {
                "some-other-tool": {},
                "py-build-cmake": {
                    "cmake": {
                        "build_type": "Release",
                        "generator": "Ninja",
                        "source_path": os.path.normpath("/project/src"),
                        "args": ["arg1", "arg2"],
                        "env": {"foo": "bar"},
                        "find_python": False,
                        "find_python3": True,
                    },
                    "cross": {
                        "implementation": "cp",
                        "version": "310",
                        "abi": "cp310",
                        "arch": "linux_aarch64",
                        "toolchain_file": os.path.normpath(
                            "/project/aarch64-linux-gnu.cmake"
                        ),
                        "cmake": {
                            "build_type": "RelWithDebInfo",
                            "generator": "Unix Makefiles",
                            "source_path": os.path.normpath("/project/src"),
                            "args": ["arg1", "arg2", "arg3", "arg4"],
                            "find_python": False,
                            "find_python3": True,
                            "env": {
                                "foo": "bar",
                                "crosscompiling": "true",
                            },
                        },
                    },
                    "linux": {
                        "cmake": {
                            "build_type": "Release",
                            "generator": "Ninja",
                            "source_path": os.path.normpath("/project/src"),
                            "args": ["arg1", "arg2"],
                            "env": {"foo": "bar"},
                            "install_components": ["linux_install"],
                            "find_python": False,
                            "find_python3": True,
                        }
                    },
                    "windows": {
                        "cmake": {
                            "build_type": "Release",
                            "generator": "Ninja",
                            "source_path": os.path.normpath("/project/src"),
                            "args": ["arg1", "arg2"],
                            "env": {"foo": "bar"},
                            "install_components": ["win_install"],
                            "find_python": False,
                            "find_python3": True,
                        }
                    },
                    "mac": {
                        "cmake": {
                            "build_type": "Release",
                            "generator": "Ninja",
                            "source_path": os.path.normpath("/project/src"),
                            "args": ["arg1", "arg2"],
                            "env": {"foo": "bar"},
                            "find_python": False,
                            "find_python3": True,
                        }
                    },
                },
            },
        }
    }

    opts.update_default_all(cfg)
    pprint(cfg.to_dict())
    assert cfg.to_dict() == {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {
                "some-other-tool": {},
                "py-build-cmake": {
                    "module": {
                        "name": "foobar",
                        "directory": os.path.normpath("/project"),
                    },
                    "editable": {
                        "mode": "wrapper",
                    },
                    "sdist": {
                        "include": [],
                        "exclude": [],
                    },
                    "cmake": {
                        "build_type": "Release",
                        "config": ["Release"],
                        "generator": "Ninja",
                        "source_path": os.path.normpath("/project/src"),
                        "build_path": os.path.normpath(
                            "/project/.py-build-cmake_cache"
                        ),
                        "options": {},
                        "args": ["arg1", "arg2"],
                        "find_python": False,
                        "find_python3": True,
                        "build_args": [],
                        "build_tool_args": [],
                        "install_args": [],
                        "install_components": [""],
                        "env": {"foo": "bar"},
                        "pure_python": False,
                        "python_abi": "auto",
                        "abi3_minimum_cpython_version": 32,
                    },
                    "cross": {
                        "implementation": "cp",
                        "version": "310",
                        "abi": "cp310",
                        "arch": "linux_aarch64",
                        "toolchain_file": os.path.normpath(
                            "/project/aarch64-linux-gnu.cmake"
                        ),
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                        "cmake": {
                            "build_type": "RelWithDebInfo",
                            "config": ["RelWithDebInfo"],
                            "generator": "Unix Makefiles",
                            "source_path": os.path.normpath("/project/src"),
                            "build_path": os.path.normpath(
                                "/project/.py-build-cmake_cache"
                            ),
                            "options": {},
                            "args": ["arg1", "arg2", "arg3", "arg4"],
                            "find_python": False,
                            "find_python3": True,
                            "build_args": [],
                            "build_tool_args": [],
                            "install_args": [],
                            "install_components": [""],
                            "env": {
                                "foo": "bar",
                                "crosscompiling": "true",
                            },
                            "pure_python": False,
                            "python_abi": "auto",
                            "abi3_minimum_cpython_version": 32,
                        },
                    },
                    "linux": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                        "cmake": {
                            "build_type": "Release",
                            "config": ["Release"],
                            "generator": "Ninja",
                            "source_path": os.path.normpath("/project/src"),
                            "build_path": os.path.normpath(
                                "/project/.py-build-cmake_cache"
                            ),
                            "options": {},
                            "args": ["arg1", "arg2"],
                            "find_python": False,
                            "find_python3": True,
                            "build_args": [],
                            "build_tool_args": [],
                            "install_args": [],
                            "install_components": ["linux_install"],
                            "env": {"foo": "bar"},
                            "pure_python": False,
                            "python_abi": "auto",
                            "abi3_minimum_cpython_version": 32,
                        },
                    },
                    "windows": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                        "cmake": {
                            "build_type": "Release",
                            "config": ["Release"],
                            "generator": "Ninja",
                            "source_path": os.path.normpath("/project/src"),
                            "build_path": os.path.normpath(
                                "/project/.py-build-cmake_cache"
                            ),
                            "options": {},
                            "args": ["arg1", "arg2"],
                            "find_python": False,
                            "find_python3": True,
                            "build_args": [],
                            "build_tool_args": [],
                            "install_args": [],
                            "install_components": ["win_install"],
                            "env": {"foo": "bar"},
                            "pure_python": False,
                            "python_abi": "auto",
                            "abi3_minimum_cpython_version": 32,
                        },
                    },
                    "mac": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                        "cmake": {
                            "build_type": "Release",
                            "config": ["Release"],
                            "generator": "Ninja",
                            "source_path": os.path.normpath("/project/src"),
                            "build_path": os.path.normpath(
                                "/project/.py-build-cmake_cache"
                            ),
                            "options": {},
                            "args": ["arg1", "arg2"],
                            "find_python": False,
                            "find_python3": True,
                            "build_args": [],
                            "build_tool_args": [],
                            "install_args": [],
                            "install_components": [""],
                            "env": {"foo": "bar"},
                            "pure_python": False,
                            "python_abi": "auto",
                            "abi3_minimum_cpython_version": 32,
                        },
                    },
                },
            },
        }
    }


def test_real_config_no_cross():
    opts = get_options(Path("/project"), test=True)
    d = {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {
                "some-other-tool": {},
                "py-build-cmake": {
                    "cmake": {
                        "build_type": "Release",
                        "generator": "Ninja",
                        "source_path": "src",
                        "env": {"foo": "bar"},
                        "args": ["arg1", "arg2"],
                        "find_python": False,
                        "find_python3": True,
                    },
                    "linux": {
                        "cmake": {
                            "install_components": ["linux_install"],
                        }
                    },
                    "windows": {
                        "cmake": {
                            "install_components": ["win_install"],
                        }
                    },
                },
            },
        }
    }
    cfg = co.ConfigNode.from_dict(d)
    opts.verify_all(cfg)
    opts.inherit_all(cfg)
    pprint(cfg.to_dict())
    opts.update_default_all(cfg)
    pprint(cfg.to_dict())
    assert cfg.to_dict() == {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {
                "some-other-tool": {},
                "py-build-cmake": {
                    "module": {
                        "name": "foobar",
                        "directory": os.path.normpath("/project"),
                    },
                    "editable": {
                        "mode": "wrapper",
                    },
                    "sdist": {
                        "include": [],
                        "exclude": [],
                    },
                    "cmake": {
                        "build_type": "Release",
                        "config": ["Release"],
                        "generator": "Ninja",
                        "source_path": os.path.normpath("/project/src"),
                        "build_path": os.path.normpath(
                            "/project/.py-build-cmake_cache"
                        ),
                        "options": {},
                        "args": ["arg1", "arg2"],
                        "find_python": False,
                        "find_python3": True,
                        "build_args": [],
                        "build_tool_args": [],
                        "install_args": [],
                        "install_components": [""],
                        "env": {"foo": "bar"},
                        "pure_python": False,
                        "python_abi": "auto",
                        "abi3_minimum_cpython_version": 32,
                    },
                    "linux": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                        "cmake": {
                            "build_type": "Release",
                            "config": ["Release"],
                            "generator": "Ninja",
                            "source_path": os.path.normpath("/project/src"),
                            "build_path": os.path.normpath(
                                "/project/.py-build-cmake_cache"
                            ),
                            "options": {},
                            "args": ["arg1", "arg2"],
                            "find_python": False,
                            "find_python3": True,
                            "build_args": [],
                            "build_tool_args": [],
                            "install_args": [],
                            "install_components": ["linux_install"],
                            "env": {"foo": "bar"},
                            "pure_python": False,
                            "python_abi": "auto",
                            "abi3_minimum_cpython_version": 32,
                        },
                    },
                    "windows": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                        "cmake": {
                            "build_type": "Release",
                            "config": ["Release"],
                            "generator": "Ninja",
                            "source_path": os.path.normpath("/project/src"),
                            "build_path": os.path.normpath(
                                "/project/.py-build-cmake_cache"
                            ),
                            "options": {},
                            "args": ["arg1", "arg2"],
                            "find_python": False,
                            "find_python3": True,
                            "build_args": [],
                            "build_tool_args": [],
                            "install_args": [],
                            "install_components": ["win_install"],
                            "env": {"foo": "bar"},
                            "pure_python": False,
                            "python_abi": "auto",
                            "abi3_minimum_cpython_version": 32,
                        },
                    },
                    "mac": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                        "cmake": {
                            "build_type": "Release",
                            "config": ["Release"],
                            "generator": "Ninja",
                            "source_path": os.path.normpath("/project/src"),
                            "build_path": os.path.normpath(
                                "/project/.py-build-cmake_cache"
                            ),
                            "options": {},
                            "args": ["arg1", "arg2"],
                            "find_python": False,
                            "find_python3": True,
                            "build_args": [],
                            "build_tool_args": [],
                            "install_args": [],
                            "install_components": [""],
                            "env": {"foo": "bar"},
                            "pure_python": False,
                            "python_abi": "auto",
                            "abi3_minimum_cpython_version": 32,
                        },
                    },
                },
            },
        }
    }


def test_real_config_no_cmake():
    opts = get_options(Path("/project"), test=True)
    d = {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {"some-other-tool": {}, "py-build-cmake": {}},
        }
    }
    cfg = co.ConfigNode.from_dict(d)
    opts.verify_all(cfg)
    opts.inherit_all(cfg)
    pprint(cfg.to_dict())
    opts.update_default_all(cfg)
    pprint(cfg.to_dict())
    assert cfg.to_dict() == {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {
                "some-other-tool": {},
                "py-build-cmake": {
                    "module": {
                        "name": "foobar",
                        "directory": os.path.normpath("/project"),
                    },
                    "editable": {
                        "mode": "wrapper",
                    },
                    "sdist": {
                        "include": [],
                        "exclude": [],
                    },
                    "linux": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                    },
                    "windows": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                    },
                    "mac": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                    },
                },
            },
        }
    }


def test_real_config_local_override():
    opts = get_options(Path("/project"), test=True)
    d = {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {"some-other-tool": {}, "py-build-cmake": {}},
        },
        "py-build-cmake.local.toml": {"sdist": {"include": ["somefile*"]}},
    }
    cfg = co.ConfigNode.from_dict(d)
    opts.verify_all(cfg)
    opts.override_all(cfg)
    opts.inherit_all(cfg)
    pprint(cfg.to_dict())
    opts.update_default_all(cfg)
    pprint(cfg.to_dict())
    assert cfg.to_dict() == {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {
                "some-other-tool": {},
                "py-build-cmake": {
                    "module": {
                        "name": "foobar",
                        "directory": os.path.normpath("/project"),
                    },
                    "editable": {
                        "mode": "wrapper",
                    },
                    "sdist": {
                        "include": ["somefile*"],
                        "exclude": [],
                    },
                    "linux": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": ["somefile*"],
                            "exclude": [],
                        },
                    },
                    "windows": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": ["somefile*"],
                            "exclude": [],
                        },
                    },
                    "mac": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": ["somefile*"],
                            "exclude": [],
                        },
                    },
                },
            },
        },
        "py-build-cmake.local.toml": {"sdist": {"include": ["somefile*"]}},
    }


def test_real_config_local_override_windows():
    opts = get_options(Path("/project"), test=True)
    d = {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {
                "some-other-tool": {},
                "py-build-cmake": {
                    # "editable":{},
                    # "sdist":{},
                },
            },
        },
        "py-build-cmake.local.toml": {
            "windows": {
                "editable": {
                    "mode": "hook",
                },
                "sdist": {"include": ["somefile*"]},
            }
        },
    }
    cfg = co.ConfigNode.from_dict(d)
    print("\ninitial")
    pprint(cfg.to_dict())
    opts.verify_all(cfg)
    print("\nverified")
    pprint(cfg.to_dict())
    opts.override_all(cfg)
    print("\noverridden")
    pprint(cfg.to_dict())
    opts.inherit_all(cfg)
    print("\ninherited")
    pprint(cfg.to_dict())
    opts.update_default_all(cfg)
    print("\ndefaulted")
    pprint(cfg.to_dict())
    assert cfg.to_dict() == {
        "pyproject.toml": {
            "project": {"name": "foobar"},
            "tool": {
                "some-other-tool": {},
                "py-build-cmake": {
                    "module": {
                        "name": "foobar",
                        "directory": os.path.normpath("/project"),
                    },
                    "editable": {
                        "mode": "wrapper",
                    },
                    "sdist": {
                        "include": [],
                        "exclude": [],
                    },
                    "linux": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                    },
                    "windows": {
                        "editable": {
                            "mode": "hook",
                        },
                        "sdist": {
                            "include": ["somefile*"],
                            "exclude": [],
                        },
                    },
                    "mac": {
                        "editable": {
                            "mode": "wrapper",
                        },
                        "sdist": {
                            "include": [],
                            "exclude": [],
                        },
                    },
                },
            },
        },
        "py-build-cmake.local.toml": {
            "windows": {
                "editable": {
                    "mode": "hook",
                },
                "sdist": {"include": ["somefile*"]},
            }
        },
    }


if __name__ == "__main__":
    test_real_config_inherit_cross_cmake()
