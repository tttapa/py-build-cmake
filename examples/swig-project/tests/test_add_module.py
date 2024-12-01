from swig_project import __version__ as py_version
from swig_project.add_module import __version__ as cpp_version
from swig_project.add_module import add


def test_add():
    assert add(1, 2) == 3


def test_version():
    assert py_version == cpp_version
    try:  # No importlib in Python 3.7 and below
        from importlib.metadata import version

        assert py_version == version("swig_project")
    except ImportError:
        pass
