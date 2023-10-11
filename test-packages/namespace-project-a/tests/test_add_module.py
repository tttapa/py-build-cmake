import sys

import pytest
from namespace_project.add_module import __version__, add


def test_add():
    assert add(1, 2) == 3


@pytest.mark.skipif(
    sys.version_info < (3, 8),
    reason="No importlib.metadata.version support on older versions of Python",
)
def test_version():
    from importlib.metadata import version

    assert __version__ == version("namespace_project_a")
