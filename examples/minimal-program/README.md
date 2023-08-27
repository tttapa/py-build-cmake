# Minimal program

Minimal example using CMake and py-build-cmake to build a C++ program and
package it as a Python package.

The key takeaway of this example is the installation path of the program: it
should be in `${PY_BUILD_CMAKE_PACKAGE_NAME}-${PY_BUILD_CMAKE_PACKAGE_VERSION}.data/scripts`,
as per [PEP 427](https://peps.python.org/pep-0427/). Pip will then automatically
install it to a folder that's in the `PATH`.  
Since there are no Python extension modules with specific ABI requirements for
the Python interpreter, `tool.py-build-cmake.cmake.python_abi` is set
to `'none'`.

For more information about the file structure and the configuration files,
please see the [`minimal` example](../minimal).
