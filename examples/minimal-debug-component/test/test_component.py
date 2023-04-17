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
    assert sys.platform != "linux" or '_add_module.so.debug' in contents
    assert sys.platform != "win32" or '_add_module.pdb' in contents
