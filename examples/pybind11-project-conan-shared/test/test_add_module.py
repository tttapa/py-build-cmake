from importlib.metadata import version
from pybind11_project_conan_shared.add_module import add
from pybind11_project_conan_shared import __version__ as py_version
from pybind11_project_conan_shared.add_module import __version__ as py_cpp_version
from pybind11_project_conan_shared._add_module import __version__ as cpp_version


def test_add():
    assert add(1, 2) == 3


def test_version():
    assert py_version == py_cpp_version
    assert py_version == cpp_version
    assert py_version == version("pybind11_project_conan_shared")
