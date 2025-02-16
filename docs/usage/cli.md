
# Command line interface

A command-line utility is provided for configuring, building and installing the
CMake project manually. Use the `--help` flag or run the command without
arguments for usage information:
```sh
py-build-cmake --help
```

To use a specific Python version, you can invoke it as follows:
```sh
python3.11 -m py_build_cmake.cli --help
```

## Use cases

One use case is generating and installing the Python stub files when
cross-compiling: you can use py-build-cmake's CLI to first perform a native
build, then install the stub files to the source directory, and then package
it using PyPA build or pip.
