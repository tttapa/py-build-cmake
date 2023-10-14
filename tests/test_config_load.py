import os
from pathlib import PurePosixPath

import pytest
from py_build_cmake.config.load import Config, ConfigError, process_config


def test_process_config_no_cmake():
    pyproj_path = PurePosixPath(os.path.normpath("/project/pyproject.toml"))
    pyproj = {
        "project": {"name": "foobar", "version": "0.0.1"},
        "tool": {"some-other-tool": {}, "py-build-cmake": {}},
    }
    files = {"pyproject.toml": pyproj}
    cfg: Config = process_config(pyproj_path, files, [], test=True)
    assert not cfg.cmake
    assert not cfg.cross
    assert not cfg.stubgen
    assert cfg.package_name == "foobar"
    assert cfg.module["name"] == "foobar"
    assert cfg.module["directory"] == os.path.normpath("/project")
    assert not cfg.module["namespace"]


def test_process_config_no_cmake_namespace_wrong_editable_mode():
    pyproj_path = PurePosixPath(os.path.normpath("/project/pyproject.toml"))
    pyproj = {
        "project": {"name": "foobar", "version": "0.0.1"},
        "tool": {
            "some-other-tool": {},
            "py-build-cmake": {
                "module": {"namespace": True},
                "editable": {"mode": "wrapper"},
            },
        },
    }
    files = {"pyproject.toml": pyproj}
    expected = "^Namespace packages cannot use editable mode 'wrapper'$"
    with pytest.raises(ConfigError, match=expected):
        process_config(pyproj_path, files, [], test=True)
