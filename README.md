[![Python Wheel](https://github.com/tttapa/py-build-cmake/actions/workflows/wheel.yml/badge.svg)](https://github.com/tttapa/py-build-cmake/actions/workflows/wheel.yml)
[![Documentation](https://img.shields.io/badge/Documentation-main-blue)](https://tttapa.github.io/py-build-cmake)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/py-build-cmake?label=PyPI)](https://pypi.org/project/py-build-cmake)

# py-build-cmake

Modern, [PEP 517](https://www.python.org/dev/peps/pep-0517/) compliant build
backend for creating Python packages with extensions built using CMake.

## Features

 - Building and packaging C, C++ or Fortran extension modules for Python using CMake
 - Declarative configuration using `pyproject.toml` ([PEP 621](https://www.python.org/dev/peps/pep-0621/))
 - Editable/development installations for Python modules ([PEP 660](https://www.python.org/dev/peps/pep-0660/))
 - Easy integration with [pybind11](https://github.com/pybind/pybind11) and [nanobind](https://github.com/wjakob/nanobind), with stable ABI support
 - Stub generation for type checking and autocompletion
 - Customizable CMake configuration, build, and installation options
 - Support for multiple installation configurations and components, across different Wheel packages
 - First-class cross-compilation support
 - Reproducible source distributions
 - No dependency on [setuptools](https://github.com/pypa/setuptools)
 - Compatible with [cibuildwheel](https://github.com/pypa/cibuildwheel) for building Wheels

## Installation

The py-build-cmake package is available on
[PyPI](https://pypi.org/project/py-build-cmake/):

```sh
pip install py-build-cmake
```

## Documentation

The documentation can be found on <https://tttapa.github.io/py-build-cmake>.

The format of the configuration file is explained in
[Config.md](https://tttapa.github.io/py-build-cmake/Config.html).

Alternatively, use the [command-line interface](https://tttapa.github.io/py-build-cmake/CLI.html)
to get the documentation for all supported options:
```sh
py-build-cmake config format
```

To get started quickly, have a look at the following section and the README in
[`examples/minimal`](https://github.com/tttapa/py-build-cmake/tree/main/examples/minimal),
which goes over the project structure and the configuration files you'll need.

## Usage

If you don't have one already, add a `pyproject.toml` configuration file to your
project's repository. Specify the mandatory project metadata ([PyPA: Declaring project metadata](https://packaging.python.org/en/latest/specifications/declaring-project-metadata)),
and tell py-build-cmake how to build your CMake project. For example:

```toml
[project] # Project metadata
name = "example-project"
readme = "README.md"
requires-python = ">=3.7"
license = { "file" = "LICENSE" }
authors = [{ "name" = "Pieter P", "email" = "pieter.p.dev@outlook.com" }]
keywords = ["some", "keywords"]
classifiers = ["Topic :: Scientific/Engineering"]
urls = { "Documentation" = "https://tttapa.github.io/py-build-cmake" }
dependencies = ["numpy"]
dynamic = ["version", "description"]

[build-system] # How pip and other frontends should build this project
requires = ["py-build-cmake~=0.2.0a13"]
build-backend = "py_build_cmake.build"

[tool.py-build-cmake.module] # Where to find the Python module to package
directory = "src-python"

[tool.py-build-cmake.sdist] # What to include in source distributions
include = ["CMakeLists.txt", "src/*"]

[tool.py-build-cmake.cmake] # How to build the CMake project
build_type = "RelWithDebInfo"
source_path = "src"
build_args = ["-j"]
install_components = ["python_modules"]

[tool.py-build-cmake.stubgen] # Whether and how to generate typed stub files
```
The README of [`examples/minimal`](https://github.com/tttapa/py-build-cmake/tree/main/examples/minimal)
describes this configuration file in much more detail.

Then use [`pip`](https://github.com/pypa/pip), [`build`](https://github.com/pypa/build)
or another PEP 517 compatible frontend to build and/or install the package.

Build sdist and wheel packages you can upload to PyPI:
```sh
python -m pip install -U build
python -m build . # find the sdist and wheel file in the 'dist' folder
```

Install the package in the current environment:
```sh
pip install .    # normal installation
pip install -e . # editable installation
```

## Examples

As an introduction to py-build-cmake, see [`examples/minimal`](https://github.com/tttapa/py-build-cmake/tree/main/examples/minimal)
for a detailed overview of the configuration files and the directory structure,
using a very simple Python module as an example.  
For a more advanced, real-world example, see [`examples/pybind11-project`](https://github.com/tttapa/py-build-cmake/tree/main/examples/pybind11-project)
and [`examples/nanobind-project`](https://github.com/tttapa/py-build-cmake/tree/main/examples/nanobind-project).  
If you are interested in packaging C/C++/Fortran programs using py-build-cmake,
have a look at [`examples/minimal-program`](https://github.com/tttapa/py-build-cmake/tree/main/examples/minimal-program).  
See the [`examples`](https://github.com/tttapa/py-build-cmake/tree/main/examples) folder for a full list of examples.

## Projects using py-build-cmake

If you need more examples, you can look at the following projects using
py-build-cmake as their Python build backend:

- [alpaqa](https://github.com/kul-optec/alpaqa/tree/develop)
- [QPALM](https://github.com/kul-optec/QPALM)

## Alternatives and related tools

- [scikit-build-core](https://github.com/scikit-build/scikit-build-core): alternative CMake build backend, successor of [scikit-build](https://github.com/scikit-build/scikit-build)
- [meson-python](https://github.com/mesonbuild/meson-python): Meson build backend
- [flit](https://github.com/pypa/flit): pure-Python packaging tool and build backend
- [hatchling](https://hatch.pypa.io/latest/config/build/#build-system): build backend of the [Hatch](https://hatch.pypa.io/latest/) project manager, supports build hooks
- [poetry-core](https://python-poetry.org/docs/pyproject/#poetry-and-pep-517): pure-Python build backend for the [Poetry](https://python-poetry.org/) package manager
- [crossenv](https://github.com/benfogle/crossenv): tool to trick `setuptools` into cross-compiling by monkey patching the `sysconfig` and `distutils` modules

## Planned features

 - [x] ~~macOS support~~
 - [x] ~~Entry point support~~
 - [ ] Namespace package support ([PEP 420](https://www.python.org/dev/peps/pep-0420/))
 - [ ] Doxygen and Sphinx support
