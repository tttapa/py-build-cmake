import re
import sys

def test_component():
    try:
        # Not available in Python 3.7, 3.8
        from importlib.resources import files
    except ImportError:
        return

    contents = [
        resource.name for resource in files('minimal_comp').iterdir()
        if resource.is_file()
    ]
    print(contents)
    if sys.platform == 'linux':
        patt = re.compile(r"^_add_module(\.\S+)?\.so\.debug$")
        assert any(map(patt.match, contents))
    if sys.platform == "win32":
        patt = re.compile(r"^_add_module(\.\S+)?\.pdb$")
        assert any(map(patt.match, contents))
