# Minimal

Minimal example using CMake and py-build-cmake to build and package a Python
extension module in C. It defines a simple C function that adds two
integers together, and exposes this function in a Python module:

```c
/* This is the addition function we wish to expose to Python. */
long add(long a, long b) {
    return a + b;
}
```
```py
# This is how to call the addition function from Python
from minimal.add_module import add

def test_add_positive():
    assert add(1, 2) == 3
```

> **Note**: While useful as an example, I don't recommend writing extension
> modules by hand.  
> Instead, consider using a library such as [pybind11](https://github.com/pybind/pybind11)
> or [nanobind](https://github.com/wjakob/nanobind) to generate Python bindings
> for your C or C++ code. Examples using py-build-cmake with pybind11 or
> nanobind can be found in [examples](../README.md).

The remainder of this tutorial first goes over the directory structure of the
package and the necessary files ([§ Package structure](#package-structure)),
then it explains the options in the `pyproject.toml` configuration file for
specifying metadata and build options ([§ Configuration](#configuration)),
and it concludes with instructions to use PyPA `build` and `pip` to build and
install the package ([§ Building and installing](#building-and-installing)).

## Package structure

We'll quickly describe the purpose of all files in this example package.
More general information about Python packages can be found at https://packaging.python.org/.

```text
minimal
   ├── src
   │   ├── add_module.c
   │   └── _add_module.pyi
   ├── src-python
   │   └── minimal
   │       ├── __init__.py
   │       ├── add_module.py
   │       └── py.typed
   ├── tests
   │   └── test_add_module.py
   ├── CMakeLists.txt
   ├── LICENSE
   ├── pyproject.toml
   └── README.md
```

`README.md`  
This file. It will be included in the Python package as the long description and
will be shown on your PyPI project page.

`pyproject.toml`  
Defines how the project is built and contains all the necessary metadata for
your package. Specifies CMake options, which files to include in the package,
as well as options for other tools. This file is covered in much more detail
below, because it is the main way you will interact with py-build-cmake's build
process.

`LICENSE`  
The software license for your package. Is included in the Python package.

`CMakeLists.txt`  
The main CMake script for the C, C++ and Fortran code. It defines how the
Python extension module will be built and installed. This is the entry point to
your project that's used by py-build-cmake (as defined in pyproject.toml).

`src`  
The folder containing all C, C++ and Fortran code that will be built using CMake.

`src/add_module.c`  
The source file for the Python extension module to be compiled. In practice,
you may have multiple directories with source code, separate libraries, etc.

`src/_add_module.pyi`  
Python stub file ([PEP 561](https://peps.python.org/pep-0561/)). Defines the
types and signatures of the functions and classes in your C extension module.
It is used by IDEs and other tools for type checking and autocompletion.
This handwritten file is provided as a simple example: in a real project,
consider using a tool to generate stubs automatically, as demonstrated in the
[pybind11-project](../pybind11-project) and [nanobind-project](../nanobind-project)
examples.

`src-python`  
Directory for the Python source files of your package.

`src-python/minimal/__init__.py`  
Marks this folder as a Python package. It also contains the brief description
and the version number that will be read by py-build-cmake and included in the
package metadata.

`src-python/minimal/add_module.py`  
Python module that simply wraps the C extension module and imports all its
contents.

`src-python/minimal/py.typed`  
Tells [mypy](https://github.com/python/mypy) to provide type checking for your
package, and to look at the stub files.

`tests/test_add_module.py`  
Unit tests for testing the extension module using [pytest](https://github.com/pytest-dev/pytest).

---

## Configuration

We'll now go over the contents of the pyproject.toml file in a bit more
detail. Keep in mind that you can always consult the [py-build-cmake documentation](https://tttapa.github.io/py-build-cmake/Config.html)
for more information about specific options. More information about the
`pyproject.toml` format can be found at https://packaging.python.org/en/latest/specifications/declaring-project-metadata/.

```toml
[build-system]
requires = ["py-build-cmake~=0.3.4.dev0"]
build-backend = "py_build_cmake.build"
```

The `build-system` section defines how tools like `pip` and `build` (called
_build front-ends_) should build your package. We state that the package should
be built using the `build` module of the `py_build_cmake` package as a backend,
and that this package should be installed before building by using the
`requires` option.
If you have other build-time requirements, you can add them to the list.

```toml
[project]
name = "minimal"
readme = "README.md"
requires-python = ">=3.7"
license = { "file" = "LICENSE" }
authors = [{ "name" = "Pieter P", "email" = "pieter.p.dev@outlook.com" }]
keywords = ["example", "addition", "subtraction"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Operating System :: POSIX :: Linux",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: MacOS",
]
urls = { "Documentation" = "https://tttapa.github.io/" }
dependencies = []
dynamic = ["version", "description"]
```

The `project` section contains all metadata of the package. Its format is
defined by [PEP 621](https://www.python.org/dev/peps/pep-0621/), see
https://packaging.python.org/en/latest/specifications/declaring-project-metadata/
for the full documentation. This metadata will be displayed on PyPI when you
publish your package.

Note that the README.md and LICENSE files are referenced here: this will cause
them to be included in the final package.

The `version` and `description` options are set to `dynamic`, which will cause
py-build-cmake to read them from your package or module dynamically (it uses
the module docstring as the description, and the `__version__` variable for the
version number). Have a look at [\_\_init\_\_.py](src-python/minimal/__init__.py)
for an example.

If your package has any runtime dependencies, you can specify them here as well.
When a user installs your package, e.g. using `pip install`, `pip` will install
these dependencies as well.  
It is recommended to add version ranges for your dependencies, see [PEP 631](https://peps.python.org/pep-0631)
for details.

```toml
[tool.py-build-cmake.module]
directory = "src-python"
```
This is the first py-build-cmake specific section: `module` defines the path
where it should look for your Python package. You can also include the `name`
option when your module or package name is different from the name of your
project on PyPI (which is determined by `[project].name`).

```toml
[tool.py-build-cmake.sdist]
include = ["CMakeLists.txt", "src/*"]
```
The `sdist` section declares which files should be included for a source
distribution. You should include everything needed to build your package, so
including the C and CMake files. The README.md and LICENSE files mentioned in
the metadata are included automatically, and so is the entire Python package
directory `src-python/minimal`.  
You can use the `exclude` option to exclude specific files. Referenced
directories are always included/excluded recursively.

```toml
[tool.py-build-cmake.cmake]
minimum_version = "3.17"
build_type = "RelWithDebInfo"
source_path = "."
build_args = ["-j"]
install_components = ["python_modules"]
```
The `cmake` section defines the settings for invoking CMake when building your
project. The most important option is the `source_path`, the folder containing
your main CMakeLists.txt file. The `-j` flag enables parallel builds, and the
`install_components` option defines which CMake components to install into the
Wheel package. In this example, the `python_modules` component is defined in
[CMakeLists.txt](CMakeLists.txt).  
The `minimum_version` option specifies which version of CMake is required to
build this project. If this version (or newer) is not found in the system PATH,
it is automatically added as a build requirement and installed by the build
frontend (e.g. pip) before building.  
There are many other options: take a moment to look at the [py-build-cmake documentation](https://tttapa.github.io/py-build-cmake/Config.html#cmake)
for an overview and more detailed explanations.

```toml
[tool.py-build-cmake.stubgen]
```
This section enables stub file generation for Python source files using mypy's
[`stubgen`](https://mypy.readthedocs.io/en/stable/stubgen.html) tool. Refer to
the [py-build-cmake documentation](https://tttapa.github.io/py-build-cmake/Config.html#stubgen)
for information about the optional options in this section.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```
You can also add configuration options for other Python tools, for example, for
`pytest`. See https://docs.pytest.org/en/7.4.x/reference/customize.html#pyproject-toml for
details.

---

## Building and installing

### Building sdists and Wheels

To distribute or publish your project, you'll need to create source and binary
distributions. The easiest way to do this is using
[PyPA build](https://github.com/pypa/build).

```sh
pip install build
```
Then go to the root folder of your project (the one containing the
pyproject.toml file), and start the build:

```sh
python -m build .
```
This will first package the source distribution, which is then used to build a
binary Wheel package for your platform. While building the Wheel, py-build-cmake
will invoke CMake to build your extension modules, and include them in the
Wheel.  
The resulting packages can be found in the `dist` folder.

You could now upload these packages to PyPI, as explained in
https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-the-distribution-archives.
For a real-world project, it is recommended to use trusted publishing as part of
a CI workflow, which is more secure and less error prone than manually
uploading the files. This is not covered by this tutorial, but you can find
more details in the [FAQ](https://tttapa.github.io/py-build-cmake/FAQ.html#how-to-upload-my-package-to-pypi).

On Linux, you'll want to use [auditwheel](https://github.com/pypa/auditwheel)
to make sure that your package is compatible with a larger range of systems.

### Installing the package locally

You can use pip to easily install your package locally. Again in the project
root directory, run:
```sh
pip install .
```
You can use the `-v` flag to display the full output of the build process
(e.g. compiler warnings).  
By default, pip builds packages in a temporary virtual environment, where it
first installs all build dependencies. This can be slow, and might not be
desirable during development. You can use the `--no-build-isolation` flag to
disable this behavior.
See https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-no-build-isolation
for more information.

### Installing the package in editable mode

While developing your package, you probably don't want to reinstall it every
time you make a change to one of the Python files. For this reason, packages
can be installed in editable mode, so changes are effective immediately.
```sh
pip install -e .
```
You can again combine it with the `-v` and/or `--no-build-isolation` flags.

By default, editable mode only affects the Python source files in your package.
If you modify the C code for any extension modules or other files generated by
CMake, you'll either have to run `pip install` to build and install them again,
or enable the [`editable.build_hook`](https://tttapa.github.io/py-build-cmake/Config.html#editable)
setting to automatically re-run `cmake --build` when your package is first
imported:
```sh
pip install -ve . --no-build-isolation -C override=editable.build_hook=true
```

### Running the tests

Thanks to the pytest configuration in pyproject.toml, you can run the tests as
follows:
```sh
pip install pytest
```
```sh
pytest
```
To see the full test output, you can use the `-rP` option.

### Cleaning the build folder

By default, a build folder with the name `.py-build-cmake_cache` in the project
root directory is created. If you make certain changes to your CMake
configuration (e.g. switching to a different generator), you might have to
delete this folder.  
There's no harm in just deleting it, and you should add it to your .gitignore
to prevent checking it in to version control.

---

## Where to go next

You may find the following resources useful:

 - [Frequently asked questions](https://tttapa.github.io/py-build-cmake/FAQ.html)
 - [Documentation index](https://tttapa.github.io/py-build-cmake)
 - [More py-build-cmake example projects](https://github.com/tttapa/py-build-cmake/tree/main/examples)
 - [Official PyPA Python Packaging User Guide](https://packaging.python.org/en/latest/)
 - [cibuildwheel documentation](https://cibuildwheel.readthedocs.io/en/stable/)
