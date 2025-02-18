# Example project using py-build-cmake and nanobind

This is an example package with a C++ extension module using
[nanobind](https://github.com/wjakob/nanobind). When building for CPython 3.12
or later, the stable ABI is used, which means that you don't need one wheel for
each version of CPython.

This example is very similar to the [pybind11-project](../pybind11-project/)
example.

For more information about the file structure and the configuration files,
please see the [`minimal` example](../minimal).
