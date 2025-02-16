# Editable Install / Development Mode

During development, you often want changes to the Python source files to
take effect immediately, without having to reinstall the package under
development. This can be done using Pip's `--editable/-e` flag:

```sh
pip install -e .
```

py-build-cmake provides three different modes for editable installs: `wrapper`,
`hook`, and `symlink`. Selecting the mode can be done in `pyproject.toml`, for
example:

```toml
[tool.py-build-cmake.editable]
mode = "symlink"
```
Alternatively, you can add it to your local configuration,
`py-build-cmake.local.toml`:

```toml
[editable]
mode = "hook"
```

> **Note**: by default, only Python files are made “editable”. You'll still have
>           to run `pip install -e .` again to rebuild your C extension modules
>           if you modify any C/C++/Fortran source files.  
>           To automatically rebuild C extension modules, set
>           `editable.mode = "symlink"` and `editable.build_hook = true` in the
>           [configuration](project:../reference/config.md).
>           See the [Build hooks](#build-hooks) section below for details.

```toml
[tool.py-build-cmake.editable]
mode = "symlink"
build_hook = true
```

The following sections go into the details of the different editable
installation modes.

## Wrapper

The `wrapper` mode installs all files generated using CMake, but not the Python
source files in your package. To make these Python files available, a wrapper
`__init__.py` file is installed that adds the source directory of your package
to the `submodule_search_locations` path of the package, and then loads the
actual `__init__.py` script (the one in your source directory).  
Additionally, a `.pth` file is installed, containing the path to your source
directory, so external tools and IDEs can locate the necessary files as well,
without actually executing the wrapper script (although not all tools support
packages spread out over multiple folders, see the `symlink` mode below).

The file structure after installation is the following:

```text
my_project
  ├── pyproject.toml
  ├── src
  │   └── my_package
  │       ├── __init__.py      (actual)
  │       └── my_module.py
  └── ...
```
```text
site-packages
  ├── my_package.pth
  ├── my_package
  │   ├── __init__.py          (wrapper)
  │   ├── _my_c_extension.pyi
  │   └── _my_c_extension.so
  ├── my_package-1.2.3.dist-info
  │   └── ...
  └── ...
```

The `__init__.py` wrapper file contains something along the lines of:

```py
# First extend the search path with the development folder
__spec__.submodule_search_locations.insert(0, '/full/path/to/my_project/src/my_package')
# Now manually import the development __init__.py
from importlib import util as _util
_spec = _util.spec_from_file_location("my_package",
                                      '/full/path/to/my_project/src/my_package/__init__.py')
_mod = _util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
# After importing, add its symbols to our global scope
_vars = _mod.__dict__.copy()
for _k in ['__builtins__','__cached__','__file__','__loader__','__name__','__package__','__path__','__spec__']: _vars.pop(_k)
globals().update(_vars)
# Clean up
del _k, _spec, _mod, _vars, _util
```

And the `my_package.pth` file contains the path to the source directory:

```py
/full/path/to/my_project/src
```

## Hook

The `hook` mode uses a `.pth` file to point to the source directory. For
pure-Python packages, this suffices, but for packages that contain C extension
modules, an extra step is required. The reason for this is that the package
will be split up into two directories, the source directory where the Python
source files live, and a directory in Python's `site-packages` directory where
the C extension modules and other generated files are installed. To be able to
locate these generated files, `hook` mode inserts a “path finder” hook into
`sys.meta_path`. For more information, see
<https://docs.python.org/3/reference/import.html#the-meta-path>.

The advantage of `hook` mode is that does not install a “fake” `__init__.py`
wrapper file that might confuse some tools. The disadvantage is that the
installed package does not include an `__init__.py` file at all, which might
confuse some other tools.

The file structure after installation is the following:

```text
my_project
  ├── pyproject.toml
  ├── src
  │   └── my_package
  │       ├── __init__.py
  │       └── my_module.py
  └── ...
```
```text
site-packages
  ├── my_package.pth
  ├── my_package               (no __init__.py here)
  │   ├── _my_c_extension.pyi
  │   └── _my_c_extension.so
  ├── my_package_editable_hook
  │   └── __init__.py
  ├── my_package-1.2.3.dist-info
  │   └── ...
  └── ...
```

The `my_package_editable_hook/__init__.py` file is responsible for actually
adding the path finder to Python's meta path:

```py
import sys, inspect, os
from importlib.machinery import PathFinder

class EditablePathFinder(PathFinder):
    def __init__(self, name, extra_path):
        self.name = name
        self.extra_path = extra_path
    def find_spec(self, name, path=None, target=None):
        if name.split('.', 1)[0] != self.name:
            return None
        if path is None:
            path = []
        path.append(self.extra_path)
        return super().find_spec(name, path, target)

def install(name: str):
    source_path = os.path.abspath(inspect.getsourcefile(EditablePathFinder))
    source_dir = os.path.dirname(source_path)
    installed_path = os.path.join(source_dir, '..', name)
    sys.meta_path.insert(0, EditablePathFinder(name, installed_path))

install('my_package')
```

This file is loaded by the `my_package.pth` file, which contains:

```py
/full/path/to/my_project/src
import my_package_editable_hook
```

## Symlink (default)

The disadvantage of the previous two methods is that they split up the package
across different folders, and not all external tools and IDEs deal with this
correctly. An alternative is to use the `symlink` mode, which installs all files
in the same folder, but uses symbolic links to the Python source files, rather
than copying them. While this mode avoids the tooling disadvantages of `wrapper`
and `hook` mode, it only works if your operating system and file system support
symbolic links.\*

The files and symlinks are installed in a hidden
`.py-build-cmake_cache/editable` folder inside of the project's source directory,
and a `.pth` file is installed so Python can locate them.
The file structure after installation is the following:

```text
my_project
  ├── pyproject.toml
  ├── src
  │   └── my_package
  │       ├── __init__.py
  │       └── my_module.py
  ├── .py-build-cmake_cache
  │   └── editable
  │       └── my_package
  │           ├── __init__.py -> /full/path/to/my_project/src/__init__.py
  │           ├── my_module.py -> /full/path/to/my_project/src/my_module.py
  │           ├── _my_c_extension.pyi
  │           └── _my_c_extension.so
  └── ...
```
```text
site-packages
  ├── my_package.pth           (no my_package folder here)
  ├── my_package-1.2.3.dist-info
  │   └── ...
  └── ...
```

The Wheel package format does not support symbolic links, so only a `.pth` file
is included in the Wheel, and the actual files and symlinks are copied to a
hidden folder in the project's source directory, [as proposed by PEP 660](https://peps.python.org/pep-0660/#what-to-put-in-the-wheel).

Note that any binaries installed into `my_package-1.2.3.data/scripts` will not
be in the path, since they are installed in the `.py-build-cmake_cache/editable`
folder, not in `site-packages/bin` or `site-packages/Scripts`.

---

## Build hooks

During development, py-build-cmake can be configured to automatically recompile
any C extension modules that changed. This is done by setting the
`editable.build_hook` option to `true`. Under the hood, this will cause a hook
to be installed in the [meta path](https://docs.python.org/3/reference/import.html#import-hooks),
which will invoke `cmake --build` and `cmake --install` when your package is
first imported.

Modern build systems like Ninja are very fast at figuring out whether anything
has to be recompiled, so the overhead of this hook is relatively low when no
files changed.

Keep in mind that C extension modules cannot be unloaded or reloaded after they
have been imported once. You need to restart the Python interpreter for any
changes to take effect. This is why the build is only carried out during the
first import (and before the module is first loaded).

To avoid depending on packages in Pip's temporary build directory or virtual
environment, you can use the `--no-build-isolation` flag:

```sh
pip install -e . --no-build-isolation
```

This requires you to install any dependencies into your environment beforehand.

The only mode that is currently supported is `symlink`. This is because
`symlink` mode installs the extension modules into a hidden folder inside of the
project folder, whereas the `hook` and `wrapper` modes include the extension
modules in the package. In such a case, the build hook would have to install its
artifacts into the Python site-packages directory directly. This comes with the
risk of installing files that were not included in the original package's RECORD
(e.g. if the user modifies any CMake code or options), and these files would not
be cleaned up when uninstalling the package. Files left behind by old packages
could cause all kinds of issues that are hard to debug, so py-build-cmake simply
does not allow this.

---

<small>

(\*) Specifically, to create symbolic links on Windows without administrator
rights, you need to enable [Developer Mode](https://learn.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development).
Otherwise, you'll see `OSError: symbolic link privilege not held` or
`[WinError 1314] A required privilege is not held by the client`. If you
cannot change the privilege, you can override the editable mode in a
`py-build-cmake.local.toml` file as described above.

</small>
