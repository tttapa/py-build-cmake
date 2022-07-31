# Minimal

Minimal example using CMake and py-build-cmake to build a Python extension 
module in C.

> **Note**: I don't recommend writing extension modules by hand.  
> Instead, use a library such as [pybind11](https://github.com/pybind/pybind11).

## Package structure

```text
minimal
   ├── src
   │   ├── add_module.c
   │   ├── _add_module.pyi
   │   └── CMakeLists.txt
   ├── src-python
   │   └── minimal
   │       ├── __init__.py
   │       ├── add_module.py
   │       └── py.typed
   ├── test
   │   └── test_add_module.py
   ├── CMakeLists.txt
   ├── LICENSE
   ├── pyproject.toml
   └── README.md
```

### README.md

This file. Will be included in the Python package as the long description and 
will be shown on your PyPI project page.

### pyproject.toml

Defines how the project is built and contains all the necessary metadata for
your package. Specifies CMake options, which files to include in the package,
as well as options for other tools. This file is covered in much more detail
below, because it is the main way you will interact with py-build-cmake's build
process.

### LICENSE

The software license for your package. Is included in the Python package.

### CMakeLists.txt

The CMake script for developer builds (used by e.g. your IDE while you're
developing your package).

### src

The folder containing all C, C++ and Fortran code, built using CMake.

### src/CMakeLists.txt

The main CMake script for the C, C++ and Fortran code. It defines how the 
Python extension module will be built and installed. This is the entry point
used by py-build-cmake (as defined in pyproject.toml).

### src/add\_module.c

The source file to be compiled. In practice, this can be much more involved,
e.g. multiple directories, separate libraries, etc.

### src/\_add\_module.pyi

Python stub file. Defines the types and signatures of the contents of your C
module. Provided as a simple example, in a real project, use a tool to generate
stubs automatically, as demonstrated in the
[pybind11-project](../pybind11-project) example.

### src-python

The Python source files of your package.

### src-python/minimal/\_\_init\_\_.py

Makes this a Python package. Also contains the brief description and the version
number that will be read by py-build-cmake and included in the package metadata.

### src-python/minimal/add\_module.py

Python module that just wraps the C extension module and imports all its
contents.

### src-python/minimal/py.typed

Tells [mypy](https://github.com/python/mypy) to provide type checking for your
package, and to look at the stub files.

### test/test\_add\_module.py

Unit tests for testing the extension module using
[pytest](https://github.com/pytest-dev/pytest).

## Configuration

We'll now go over the contents of the contents of pyproject.toml in a bit more
detail.

```toml
[build-system]
requires = ["py-build-cmake~=0.0.11"]
build-backend = "py_build_cmake.build"
```

The `build-system` section defines how tools like `pip` and `build` (called
build front-ends) should build your package. We state that the package should be
built using the `build` module of the `py_build_cmake` package as a backend,
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
keywords = ["addition", "subtraction", "pybind11"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Operating System :: POSIX :: Linux",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: MacOS",
]
urls = { "Documentation" = "https://tttapa.github.io/" }
dependencies = []
dynamic = ["version", "description"]
```

The `project` section contains all metadata of the package. Its format is 
defined in [PEP 621](https://www.python.org/dev/peps/pep-0621/), see 
https://packaging.python.org/en/latest/specifications/declaring-project-metadata/
for the full documentation. This metadata will be displayed on PyPI when you
publish your package.

Note that the README.md and LICENSE files are referenced here, this will cause
them to be included in the final package.

The `version` and `description` options are set to `dynamic`, which will cause
py-build-cmake to read them from your package or module dynamically (it uses
the module docstring as the description, and the `__version__` variable for the
version number). Have a look at [\_\_init\_\_.py](src-python/minimal/__init__.py)
for an example.

If your package has runtime dependencies, you can specify them here as well.
When a user installs your package, e.g. using `pip install`, `pip` will install
these dependencies as well.

```toml
[tool.py-build-cmake.module]
directory = "src-python"
```
This is the first py-build-cmake specific section: `module` defines the path
where it should look for your Python package. You can also include the `name`
option when your module or package name is different than the name of your 
project on PyPI.

```toml
[tool.py-build-cmake.sdist]
include = ["CMakeLists.txt", "src/*"]
```
The `sdist` section declares which files should be included for a source
distribution. You should include everything needed to build your package, so
including the C and CMake files. The README.md and LICENSE files mentioned in
the metadata are included automatically, and so is the entire Python package
directory.  
You can use the `exclude` option to exclude specific files.

```toml
[tool.py-build-cmake.cmake]
minimum_version = "3.17"
build_type = "RelWithDebInfo"
source_path = "src"
build_args = ["-j"]
install_components = ["python_modules"]
```
The `cmake` section defines the settings for invoking CMake when building your
project. The most important option is the `source_path`, the folder containing
your main CMakeLists.txt file. The `-j` flag enables parallel builds, and the 
`install_components` option defines which CMake components to install. In this
example, the `python_modules` component is defined in [src/CMakeLists.txt](src/CMakeLists.txt).  
The `minimum_version` option defines which version of CMake is required to build
this project. If this version or newer is not found in the PATH, it is added as
a build requirement and installed by the build frontend (e.g. pip) before 
building.  
There are many other options, see the [py-build-cmake documentation](https://tttapa.github.io/py-build-cmake/Config.html)
for more details.

```toml
[tool.py-build-cmake.stubgen]
```
This section enables stub file generation for Python source files using mypy's
[`stubgen`](https://mypy.readthedocs.io/en/stable/stubgen.html). Refer to the
py-build-cmake documentation for information about the optional options in this
section.

```toml
[tool.pytest.ini_options]
minversion = "6.0"
testpaths = ["test"]
```
You can also add configuration options for other Python tools, for example, for
`pytest`. See https://docs.pytest.org/en/6.2.x/customize.html#pyproject-toml for
details.

## Building sdists and wheels

To distribute or publish your project, you'll need to package source and binary
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
This will first package the source distribution, and then use that to build a
binary wheel package for your platform. While building the wheel, py-build-cmake
will invoke CMake to build your extension modules, and include them in the 
wheel.  
The resulting packages can be found in the dist folder.

You could upload these packages to PyPI, as explained in 
https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-the-distribution-archives.

On Linux, you might want to use [auditwheel](https://github.com/pypa/auditwheel)
to make your package compatible with a larger range of systems.

## Installing the package locally

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

## Installing the package in editable mode

While developing your package, you probably don't want to reinstall it every
time you make a change to one of the Python files. For this reason, packages
can be installed in editable mode, so changes are effective immediately.
```sh
pip install -e .
```
You can again combine it with the `-v` and/or `--no-build-isolation` flags.

Editable mode only affects the Python source files in your package, if you 
modify the C code for the extension modules or other files generated by CMake,
you'll have to run `pip install` to build and install them again.

## Running the tests

Thanks to the pytest configuration in pyproject.toml, you can run the tests as
follows:
```sh
pip install pytest
```
```sh
pytest
```
To see the full test output, you can use the `-rP` option.

## Cleaning the build folder

By default, a build folder with the name `.py-build-cmake_cache` in the project
root directory is created. If you make certain changes to your CMake 
configuration (e.g. switching to a different generator), you might have to 
delete this folder.  
There's no harm in just deleting it, and you should add it to your .gitignore
to prevent checking it in to version control.
