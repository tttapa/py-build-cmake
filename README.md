# py-build-cmake

Modern, [PEP 517](https://www.python.org/dev/peps/pep-0517/) compliant build
backend for building Python packages with extensions built using CMake.

## Features

 - Build C, C++ or Fortran extensions
 - Generate stubs for type checking and suggestions
 - Compatible with [pybind11](https://github.com/pybind/pybind11)
 - Declarative configuration using `pyproject.toml` ([PEP 621](https://www.python.org/dev/peps/pep-0621/)), compatible with
   [flit](https://github.com/pypa/flit)
 - Customizable CMake configuration, build and installation options
 - Support for multiple installation configurations
 - Editable/development installations for Python modules ([PEP 660](https://www.python.org/dev/peps/pep-0660/))
 - No dependency on [setuptools](https://github.com/pypa/setuptools)

## Planned features

 - Entry point support
 - `sdist` support
 - Namespace package support ([PEP 420](https://www.python.org/dev/peps/pep-0420/))
 - Doxygen and Sphinx support
 - Windows support
 - OSX support
