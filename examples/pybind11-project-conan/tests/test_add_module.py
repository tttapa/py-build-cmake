from pybind11_project_conan import __version__ as py_version
from pybind11_project_conan._add_module import __version__ as cpp_version
from pybind11_project_conan.add_module import __version__ as py_cpp_version
from pybind11_project_conan.add_module import add


def test_add():
    assert add(1, 2) == 3


def test_version():
    assert py_version == py_cpp_version
    assert py_version == cpp_version
    try:  # No importlib in Python 3.7 and below
        from importlib.metadata import version  # noqa: PLC0415

        assert py_version == version("pybind11_project_conan")
    except ImportError:
        pass
