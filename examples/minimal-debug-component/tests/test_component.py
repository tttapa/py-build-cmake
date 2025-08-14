import re
import sys

import pytest


@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="No importlib.resources support on older versions of Python",
)
@pytest.mark.skipif(
    sys.platform not in ["linux", "win32"],
    reason="No separate debug symbol files on macOS",
)
def test_component():
    from importlib.resources import files  # noqa: PLC0415

    contents = [
        resource.name
        for resource in files("minimal_comp").iterdir()
        if resource.is_file()
    ]
    print(contents)
    if sys.platform == "linux":
        patt = re.compile(r"^_add_module(\.\S+)?\.so\.debug$")
        assert any(map(patt.match, contents))
    if sys.platform == "win32":
        patt = re.compile(r"^_add_module(\.\S+)?\.pdb$")
        assert any(map(patt.match, contents))
