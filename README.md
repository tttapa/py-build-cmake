[![Python Wheel](https://github.com/tttapa/py-build-cmake/actions/workflows/wheel.yml/badge.svg)](https://github.com/tttapa/py-build-cmake/actions/workflows/wheel.yml)

# py-build-cmake

Modern, [PEP 517](https://www.python.org/dev/peps/pep-0517/) compliant build
backend for building Python packages with extensions built using CMake.

## Features

 - Build C, C++ or Fortran extensions for Python using CMake
 - Declarative configuration using `pyproject.toml` ([PEP 621](https://www.python.org/dev/peps/pep-0621/)), compatible with
   [flit](https://github.com/pypa/flit)
 - Compatible with [pybind11](https://github.com/pybind/pybind11)
 - Generate stubs for type checking and suggestions
 - Customizable CMake configuration, build and installation options
 - Support for multiple installation configurations
 - Editable/development installations for Python modules ([PEP 660](https://www.python.org/dev/peps/pep-0660/))
 - No dependency on [setuptools](https://github.com/pypa/setuptools)

## Planned features

 - Entry point support
 - Namespace package support ([PEP 420](https://www.python.org/dev/peps/pep-0420/))
 - Doxygen and Sphinx support
 - OSX support

## Installation

The py-build-cmake package is available on
[PyPI](https://pypi.org/project/py-build-cmake/):

```sh
pip install py-build-cmake
```

## Usage

Add a `pyproject.toml` configuration file
(see [`examples/minimal`](examples/minimal) for detailed instructions), and use
[`pip`](https://github.com/pypa/pip), [`build`](https://github.com/pypa/build)
or another PEP 517 compatible frontend to install and/or build the package.

Build sdist and wheel packages you can upload to PyPI:
```sh
python -m build . # find the sdist and wheel file in the 'dist' folder
```

Install the package in the current environment:
```sh
pip install . # normal installation
```
```sh
pip install -e . # editable installation
```

## Examples

For example usage, see the [`examples/minimal`](examples/minimal) and
[`examples/pybind11-project`](examples/pybind11-project) example projects.
