from py_build_cmake.add_module import add


def test_add():
    assert add(1, 2) == 3


from py_build_cmake import __version__ as py_version
from py_build_cmake.add_module import __version__ as py_cpp_version
from py_build_cmake._add_module import __version__ as cpp_version
from importlib.metadata import version


def test_version():
    assert py_version == py_cpp_version
    assert py_version == cpp_version
    assert py_version == version('py_build_cmake')
