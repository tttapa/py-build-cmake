import os
from pathlib import PurePosixPath

import pytest
from py_build_cmake.config.cli_override import parse_file
from py_build_cmake.config.load import (
    Config,
    ConfigError,
    add_cli_override,
    process_config,
)
from py_build_cmake.config.options.config_path import ConfPath


def test_process_config_no_cmake():
    pyproj_path = PurePosixPath("/project/pyproject.toml")
    pyproj = {
        "project": {"name": "foobar", "version": "0.0.1"},
        "tool": {"some-other-tool": {}, "py-build-cmake": {}},
    }
    files = {"pyproject.toml": pyproj}
    cfg: Config = process_config(pyproj_path, files, {}, test=True)
    assert not cfg.cmake
    assert not cfg.cross
    assert not cfg.stubgen
    assert cfg.package_name == "foobar"
    assert cfg.module["name"] == "foobar"
    assert cfg.module["directory"] == PurePosixPath("/project")
    assert not cfg.module["namespace"]


def test_process_config_no_cmake_namespace_wrong_editable_mode():
    pyproj_path = PurePosixPath("/project/pyproject.toml")
    pyproj = {
        "project": {"name": "foobar", "version": "0.0.1"},
        "tool": {
            "some-other-tool": {},
            "py-build-cmake": {
                "module": {"namespace": True},
                "editable": {"build_hook": False, "mode": "wrapper"},
            },
        },
    }
    files = {"pyproject.toml": pyproj}
    expected = "^Namespace packages cannot use editable mode 'wrapper'$"
    with pytest.raises(ConfigError, match=expected):
        process_config(pyproj_path, files, {}, test=True)


def test_inherit_cross_cmake():
    pyproj_path = PurePosixPath("/project/pyproject.toml")
    pyproj = {
        "project": {"name": "foobar", "version": "1.2.3", "description": "descr"},
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
                    "install_components": ["all_install"],
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
                        "args": ["linux_arg"],
                        "install_components": ["linux_install"],
                    }
                },
                "windows": {
                    "cmake": {
                        "args": {
                            "-": ["arg1"],
                            "prepend": ["win_arg"],
                            "+": ["arg1"],
                        },
                        "install_components": {"+": ["win_install"]},
                    }
                },
            },
        },
    }
    files = {"pyproject.toml": pyproj}
    conf = process_config(pyproj_path, files, {}, test=True)
    assert conf.standard_metadata.name == "foobar"
    assert str(conf.standard_metadata.version) == "1.2.3"
    assert conf.standard_metadata.description == "descr"
    assert conf.module == {
        "name": "foobar",
        "directory": PurePosixPath("/project"),
        "namespace": False,
    }
    assert conf.editable == {
        "cross": {"build_hook": False, "mode": "symlink"},
        "linux": {"build_hook": False, "mode": "symlink"},
        "windows": {"build_hook": False, "mode": "symlink"},
        "mac": {"build_hook": False, "mode": "symlink"},
    }
    assert conf.sdist == {
        "cross": {"include_patterns": [], "exclude_patterns": []},
        "linux": {"include_patterns": [], "exclude_patterns": []},
        "windows": {"include_patterns": [], "exclude_patterns": []},
        "mac": {"include_patterns": [], "exclude_patterns": []},
    }
    assert conf.cmake == {
        "cross": {
            "0": {
                "build_type": "RelWithDebInfo",
                "config": ["RelWithDebInfo"],
                "generator": "Unix Makefiles",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {},
                "args": ["arg1", "arg2", "arg3", "arg4"],
                "find_python": False,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": [],
                "install_args": [],
                "install_components": ["all_install"],
                "minimum_version": "3.15",
                "env": {
                    "foo": "bar",
                    "crosscompiling": "true",
                },
            },
        },
        "linux": {
            "0": {
                "build_type": "Release",
                "config": ["Release"],
                "generator": "Ninja",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {},
                "args": ["arg1", "arg2", "linux_arg"],
                "find_python": False,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": [],
                "install_args": [],
                "install_components": ["linux_install"],
                "minimum_version": "3.15",
                "env": {"foo": "bar"},
            },
        },
        "windows": {
            "0": {
                "build_type": "Release",
                "config": ["Release"],
                "generator": "Ninja",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {},
                "args": ["win_arg", "arg2", "arg1"],
                "find_python": False,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": [],
                "install_args": [],
                "install_components": ["all_install", "win_install"],
                "minimum_version": "3.15",
                "env": {"foo": "bar"},
            }
        },
        "mac": {
            "0": {
                "build_type": "Release",
                "config": ["Release"],
                "generator": "Ninja",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {},
                "args": ["arg1", "arg2"],
                "find_python": False,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": [],
                "install_args": [],
                "install_components": ["all_install"],
                "minimum_version": "3.15",
                "env": {"foo": "bar"},
            }
        },
    }
    assert conf.wheel == {
        "cross": {
            "python_tag": ["auto"],
            "python_abi": "auto",
            "abi3_minimum_cpython_version": 32,
        },
        "linux": {
            "python_tag": ["auto"],
            "python_abi": "auto",
            "abi3_minimum_cpython_version": 32,
        },
        "windows": {
            "python_tag": ["auto"],
            "python_abi": "auto",
            "abi3_minimum_cpython_version": 32,
        },
        "mac": {
            "python_tag": ["auto"],
            "python_abi": "auto",
            "abi3_minimum_cpython_version": 32,
        },
    }
    assert conf.cross == {
        "implementation": "cp",
        "version": "310",
        "abi": "cp310",
        "arch": "linux_aarch64",
        "toolchain_file": PurePosixPath("/project/aarch64-linux-gnu.cmake"),
    }


def test_real_config_no_cross():
    pyproj_path = PurePosixPath("/project/pyproject.toml")
    pyproj = {
        "project": {"name": "foobar", "version": "1.2.3", "description": "descr"},
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
    files = {"pyproject.toml": pyproj}
    conf = process_config(pyproj_path, files, {}, test=True)
    assert conf.standard_metadata.name == "foobar"
    assert str(conf.standard_metadata.version) == "1.2.3"
    assert conf.standard_metadata.description == "descr"
    assert conf.module == {
        "name": "foobar",
        "directory": PurePosixPath("/project"),
        "namespace": False,
    }
    assert conf.editable == {
        "linux": {"build_hook": False, "mode": "symlink"},
        "windows": {"build_hook": False, "mode": "symlink"},
        "mac": {"build_hook": False, "mode": "symlink"},
    }
    assert conf.sdist == {
        "linux": {"include_patterns": [], "exclude_patterns": []},
        "windows": {"include_patterns": [], "exclude_patterns": []},
        "mac": {"include_patterns": [], "exclude_patterns": []},
    }
    assert conf.cmake == {
        "linux": {
            "0": {
                "build_type": "Release",
                "config": ["Release"],
                "generator": "Ninja",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {},
                "args": ["arg1", "arg2"],
                "find_python": False,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": [],
                "install_args": [],
                "install_components": ["linux_install"],
                "minimum_version": "3.15",
                "env": {"foo": "bar"},
            }
        },
        "windows": {
            "0": {
                "build_type": "Release",
                "config": ["Release"],
                "generator": "Ninja",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {},
                "args": ["arg1", "arg2"],
                "find_python": False,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": [],
                "install_args": [],
                "install_components": ["win_install"],
                "minimum_version": "3.15",
                "env": {"foo": "bar"},
            }
        },
        "mac": {
            "0": {
                "build_type": "Release",
                "config": ["Release"],
                "generator": "Ninja",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {},
                "args": ["arg1", "arg2"],
                "find_python": False,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": [],
                "install_args": [],
                "install_components": [""],
                "minimum_version": "3.15",
                "env": {"foo": "bar"},
            },
        },
    }
    assert conf.wheel == {
        "linux": {
            "python_tag": ["auto"],
            "python_abi": "auto",
            "abi3_minimum_cpython_version": 32,
        },
        "windows": {
            "python_tag": ["auto"],
            "python_abi": "auto",
            "abi3_minimum_cpython_version": 32,
        },
        "mac": {
            "python_tag": ["auto"],
            "python_abi": "auto",
            "abi3_minimum_cpython_version": 32,
        },
    }
    assert conf.cross is None


def test_real_config_no_cmake():
    pyproj_path = PurePosixPath("/project/pyproject.toml")
    pyproj = {
        "project": {"name": "foobar", "version": "1.2.3", "description": "descr"},
        "tool": {"some-other-tool": {}, "py-build-cmake": {}},
    }
    files = {"pyproject.toml": pyproj}
    conf = process_config(pyproj_path, files, {}, test=True)
    assert conf.standard_metadata.name == "foobar"
    assert str(conf.standard_metadata.version) == "1.2.3"
    assert conf.standard_metadata.description == "descr"
    assert conf.module == {
        "name": "foobar",
        "directory": PurePosixPath("/project"),
        "namespace": False,
    }
    assert conf.editable == {
        "linux": {"build_hook": False, "mode": "symlink"},
        "windows": {"build_hook": False, "mode": "symlink"},
        "mac": {"build_hook": False, "mode": "symlink"},
    }
    assert conf.sdist == {
        "linux": {"include_patterns": [], "exclude_patterns": []},
        "windows": {"include_patterns": [], "exclude_patterns": []},
        "mac": {"include_patterns": [], "exclude_patterns": []},
    }
    assert conf.cmake is None
    assert conf.cross is None


def test_real_config_local_override():
    pyproj_path = PurePosixPath("/project/pyproject.toml")
    pyproj = {
        "project": {"name": "foobar", "version": "1.2.3", "description": "descr"},
        "tool": {"some-other-tool": {}, "py-build-cmake": {}},
    }
    local = {
        "sdist": {"include": ["somefile*"]},
    }
    files = {"pyproject.toml": pyproj, "/some/path/py-build-cmake.local.toml": local}
    overrides = {
        ConfPath(("/some/path/py-build-cmake.local.toml",)): ConfPath(
            ("pyproject.toml", "tool", "py-build-cmake")
        ),
    }
    conf = process_config(pyproj_path, files, overrides, test=True)
    assert conf.standard_metadata.name == "foobar"
    assert str(conf.standard_metadata.version) == "1.2.3"
    assert conf.standard_metadata.description == "descr"
    assert conf.module == {
        "name": "foobar",
        "directory": PurePosixPath("/project"),
        "namespace": False,
    }
    assert conf.editable == {
        "linux": {"build_hook": False, "mode": "symlink"},
        "windows": {"build_hook": False, "mode": "symlink"},
        "mac": {"build_hook": False, "mode": "symlink"},
    }
    assert conf.sdist == {
        "linux": {"include_patterns": ["somefile*"], "exclude_patterns": []},
        "windows": {"include_patterns": ["somefile*"], "exclude_patterns": []},
        "mac": {"include_patterns": ["somefile*"], "exclude_patterns": []},
    }
    assert conf.cmake is None
    assert conf.cross is None


def test_real_config_local_override_windows():
    pyproj_path = PurePosixPath("/project/pyproject.toml")
    pyproj = {
        "project": {"name": "foobar", "version": "1.2.3", "description": "descr"},
        "tool": {"some-other-tool": {}, "py-build-cmake": {}},
    }
    local = {
        "windows": {
            "editable": {
                "mode": "hook",
            },
            "sdist": {"include": ["somefile*"]},
        }
    }
    files = {"pyproject.toml": pyproj, "/some/path/py-build-cmake.local.toml": local}
    overrides = {
        ConfPath(("/some/path/py-build-cmake.local.toml",)): ConfPath(
            ("pyproject.toml", "tool", "py-build-cmake")
        ),
    }
    conf = process_config(pyproj_path, files, overrides, test=True)
    assert conf.standard_metadata.name == "foobar"
    assert str(conf.standard_metadata.version) == "1.2.3"
    assert conf.standard_metadata.description == "descr"
    assert conf.module == {
        "name": "foobar",
        "directory": PurePosixPath("/project"),
        "namespace": False,
    }
    assert conf.editable == {
        "linux": {"build_hook": False, "mode": "symlink"},
        "windows": {"build_hook": False, "mode": "hook"},
        "mac": {"build_hook": False, "mode": "symlink"},
    }
    assert conf.sdist == {
        "linux": {"include_patterns": [], "exclude_patterns": []},
        "windows": {"include_patterns": ["somefile*"], "exclude_patterns": []},
        "mac": {"include_patterns": [], "exclude_patterns": []},
    }
    assert conf.cmake is None
    assert conf.cross is None


def test_real_config_cli_override():
    pyproj_path = PurePosixPath("/project/pyproject.toml")
    pyproj = {
        "project": {"name": "foobar", "version": "1.2.3", "description": "descr"},
        "tool": {
            "some-other-tool": {},
            "py-build-cmake": {
                "cmake": {
                    "build_type": "Release",
                    "generator": "Ninja",
                    "source_path": "src",
                    "env": {"foo": "bar"},
                    "args": ["arg1", "arg2"],
                    "build_tool_args": ["-a", "-b"],
                    "find_python": False,
                    "find_python3": True,
                },
                "wheel": {
                    "python_abi": "abi3",
                },
                "linux": {
                    "cmake": {
                        "install_components": ["linux_install"],
                        "env": {"PATH": "/usr/bin"},
                        "args": ["arg3", "arg4"],
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
    files = {"pyproject.toml": pyproj}
    override_config = r"""
        linux.cmake.build_type=MinSizeRel
        linux.cmake.env.PATH=+(path)$HOME/opt
        linux.cmake.options.FOOBAR="abc"
        linux.cmake.options.FOOBAR+="def"
        linux.cmake.options.FOOBAR+="ghi"
        linux.cmake.options.FOOBAR=+"xyz"
        linux.cmake.options.FOOBAR-="def"
        linux.cmake.args-=["arg3"]
        linux.wheel.python_abi=!
        mac.wheel.python_abi="none"
        mac.cmake.args=!
        mac.cmake.env=!
        mac.cmake.find_python=!
        cmake.build_tool_args=["-c", "-d"]
    """
    overrides = {}
    for i, opt in enumerate(parse_file(override_config)):
        overrides.update(add_cli_override(files, opt, f"<cli:{i+1}>"))

    conf = process_config(pyproj_path, files, overrides, test=True)
    assert conf.standard_metadata.name == "foobar"
    assert str(conf.standard_metadata.version) == "1.2.3"
    assert conf.standard_metadata.description == "descr"
    assert conf.module == {
        "name": "foobar",
        "directory": PurePosixPath("/project"),
        "namespace": False,
    }
    assert conf.editable == {
        "linux": {"build_hook": False, "mode": "symlink"},
        "windows": {"build_hook": False, "mode": "symlink"},
        "mac": {"build_hook": False, "mode": "symlink"},
    }
    assert conf.sdist == {
        "linux": {"include_patterns": [], "exclude_patterns": []},
        "windows": {"include_patterns": [], "exclude_patterns": []},
        "mac": {"include_patterns": [], "exclude_patterns": []},
    }
    assert conf.cmake == {
        "linux": {
            "0": {
                "build_type": "MinSizeRel",
                "config": ["MinSizeRel"],
                "generator": "Ninja",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {"FOOBAR": "xyz;abc;ghi"},
                "args": ["arg1", "arg2", "arg4"],
                "find_python": False,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": ["-c", "-d"],
                "install_args": [],
                "install_components": ["linux_install"],
                "minimum_version": "3.15",
                "env": {"PATH": "$HOME/opt" + os.pathsep + "/usr/bin", "foo": "bar"},
            }
        },
        "windows": {
            "0": {
                "build_type": "Release",
                "config": ["Release"],
                "generator": "Ninja",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {},
                "args": ["arg1", "arg2"],
                "find_python": False,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": ["-c", "-d"],
                "install_args": [],
                "install_components": ["win_install"],
                "minimum_version": "3.15",
                "env": {"foo": "bar"},
            }
        },
        "mac": {
            "0": {
                "build_type": "Release",
                "config": ["Release"],
                "generator": "Ninja",
                "source_path": PurePosixPath("/project/src"),
                "build_path": PurePosixPath(
                    "/project/.py-build-cmake_cache/{build_config}"
                ),
                "options": {},
                "args": [],
                "find_python": True,
                "find_python3": True,
                "build_args": [],
                "build_tool_args": ["-c", "-d"],
                "install_args": [],
                "install_components": [""],
                "minimum_version": "3.15",
                "env": {},
            },
        },
    }
    assert conf.wheel == {
        "linux": {
            "python_tag": ["auto"],
            "python_abi": "auto",
            "abi3_minimum_cpython_version": 32,
        },
        "windows": {
            "python_tag": ["auto"],
            "python_abi": "abi3",
            "abi3_minimum_cpython_version": 32,
        },
        "mac": {
            "python_tag": ["auto"],
            "python_abi": "none",
            "abi3_minimum_cpython_version": 32,
        },
    }
    assert conf.cross is None
