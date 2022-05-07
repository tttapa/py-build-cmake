# Minimal program

Minimal example using CMake and py-build-cmake to build a C++ program and 
package it as a Python package.

The key point of this example is the installation path of the program: it should
be in `${PY_BUILD_CMAKE_PACKAGE_NAME}-${PY_BUILD_CMAKE_PACKAGE_VERSION}.data/scripts`,
as per [PEP 427](https://peps.python.org/pep-0427/).