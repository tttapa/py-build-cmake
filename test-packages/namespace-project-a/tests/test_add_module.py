from namespace_project.add_module import __version__, add


def test_add():
    assert add(1, 2) == 3


def test_version():
    from importlib.metadata import version  # noqa: PLC0415

    assert __version__ == version("namespace_project_a")
