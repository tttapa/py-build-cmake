[![Python Wheel (Linux)](https://github.com/tttapa/py-build-cmake/actions/workflows/wheel.yml/badge.svg)](https://github.com/tttapa/py-build-cmake/actions/workflows/wheel.yml)

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

## Usage

Add a `pyproject.toml` configuration file
(see [`pyproject.toml`](pyproject.toml) for an example), and use
[pip](https://github.com/pypa/pip), [PyPA build](https://github.com/pypa/build)
or another PEP 517 compatible frontend to install and/or build the package.

```sh
python -m build . # find the sdist and wheel file in the dist folder
```

```sh
pip install . # normal installation
```
```sh
pip install -e . # editable installation
```
