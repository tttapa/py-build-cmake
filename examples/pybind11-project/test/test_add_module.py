from pybind11_project.add_module import add


def test_add():
    assert add(1, 2) == 3


from pybind11_project import __version__ as py_version
from pybind11_project.add_module import __version__ as py_cpp_version
from pybind11_project._add_module import __version__ as cpp_version
from importlib.metadata import version


def test_version():
    assert py_version == py_cpp_version
    assert py_version == cpp_version
    assert py_version == version('pybind11_project')
