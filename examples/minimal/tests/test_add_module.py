import pytest
from minimal.add_module import add


def test_add_positive():
    assert add(1, 2) == 3


def test_add_negative():
    assert add(1, -2) == -1


def test_add_string():
    with pytest.raises(TypeError):
        add("foo", "bar")
