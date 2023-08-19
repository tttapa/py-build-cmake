<small>[Index](index.html)</small>

# Cross-compilation

Cross-compiling Python extension modules is supported out of the box through 
[CMake toolchain files](https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html).

## Terminology

- Build system: the system used for building, on which py-build-cmake is 
  invoked.
- Host system: the system that the compiled binaries and Python modules will be
  used on.
- Cross-build: building on the _build_ system, for the _host_ system.
- Native build: building on _build_ system, for the _build_ system (this is the
  usual scenario).

In cross-compilation, the build and host systems are often different systems 
with different architectures.

## Simple example

If your CMake project supports cross-compilation, cross-compiling a Python 
package can be achieved by simply adding a `py-build-cmake.cross.toml` file
to the same directory as `pyproject.toml`. This file should contain the 
necessary information about the host system, such as the Python version, 
implementation and ABI, the host operating system and architecture, and the
relative path of the CMake toolchain file to use.

For example:
```toml
implementation = 'cp'  # CPython
version = '39'         # 3.9
abi = 'cp39'           # (default ABI for CPython 3.9)
arch = 'linux_aarch64'
toolchain_file = 'aarch64-linux-gnu.cmake'
```
This will generate a package for CPython 3.9 on Linux for 64-bit ARM, using the
compilers defined by the toolchain file `aarch64-linux-gnu.cmake` (which you
should provide as well).

The format for the values in this file is the same as the format used for the 
tags in wheel filenames, for example `package-1.2.3-cp39-cp39-linux_aarch64.whl`.
For details about platform compatibility tags, see the PyPA specification:
https://packaging.python.org/en/latest/specifications/platform-compatibility-tags.

For more information about cross-compilation, ready-to-use toolchains, and 
example toolchain files, see <https://tttapa.github.io/Pages/Raspberry-Pi/C++-Development-Ubuntu>.

### Caveats

Note that `py-build-cmake` does not check the Python version when
cross-compiling, so make sure that your CMakeLists.txt scripts find the correct
Python installation (on that matches the version, implementation, ABI, operating
system and architecture specified in the `py-build-cmake.cross.toml` file),
e.g. by setting the appropriate hints and artifacts variables:

- <https://cmake.org/cmake/help/latest/module/FindPython3.html#hints>
- <https://cmake.org/cmake/help/latest/module/FindPython3.html#artifacts-specification>

You can either specify these in your toolchain file, or in the
`py-build-cmake.cross.toml` configuration, for example:

```toml
[cmake.options]
Python3_LIBRARY = "/path-to-sysroot/usr/lib/aarch64-linux-gnu/libpython3.9.so"
Python3_INCLUDE_DIR = "/path-to-sysroot/usr/include/python3.9"
```

You can find a full example in [examples/pybind11-project/py-build-cmake.cross.example.toml](https://github.com/tttapa/py-build-cmake/blob/main/examples/pybind11-project/py-build-cmake.cross.example.toml).

## Automatic cross-compilation

In order to ensure compatibility with [`cibuildwheel`](https://github.com/pypa/cibuildwheel),
`py-build-cmake` automatically enables cross-compilation when certain
environment variables are set.

### Windows

Cross-compilation on Windows is enabled if the following conditions are satisfied:

0. The configuration does not yet contain a `[tool.py-build-cmake.cross]` entry,
1. and the `DIST_EXTRA_CONFIG` environment variable is set,
2. and that variable points to a configuration file that specifies
   `build_ext.plat_name`,
3. and that value differs from the current platform.

The supported values for `build_ext.plat_name` are:
 - `win32`
 - `win-amd64`
 - `win-arm32`
 - `win-arm64`

As a result, `py-build-cmake` sets the `CMAKE_SYSTEM_NAME`,
`CMAKE_SYSTEM_PROCESSOR` and `CMAKE_GENERATOR_PLATFORM` CMake options to the
appropriate values for the given `plat_name`.  
If `build_ext.library_dirs` is set in the configuration file as well, those
directories are searched for the Python library, and if found, the
CMake `{Python,Python3}_LIBRARY` hints are specified. If the Python library is
part of a Python installation hierarchy that also contains an `include`
directory, this is specified using the `{Python,Python3}_INCLUDE_DIR` hints.  
Other CMake options are inherited from the `[tool.py-build-cmake.windows.cmake]`
configuration in `pyproject.toml`.

### macOS

Cross-compilation on macOS is enabled if the following conditions are satisfied:

0. The configuration does not yet contain a `[tool.py-build-cmake.cross]` entry,
1. and the `ARCHFLAGS` environment variable is set,
2. and its value contains one or more flags of the form `-arch XXX`,
where `XXX` is either `x86_64` or `arm64`,
3. and the current platform's architecture is not included in this list.

The supported values for `ARCHFLAGS` are:
 - `-arch x86_64` (Intel)
 - `-arch arm64` (Apple silicon)
 - `-arch x86_64 -arch arm64` (Universal 2 fat binaries, both Intel and Apple
   silicon)

As a result, `py-build-cmake` sets the `CMAKE_SYSTEM_NAME` and
`CMAKE_OSX_ARCHITECTURES` CMake options to the appropriate values.  
If the current interpreter is CPython, the `SETUPTOOLS_EXT_SUFFIX` environment
variable is set as well.  
Other CMake options are inherited from the `[tool.py-build-cmake.mac.cmake]`
configuration in `pyproject.toml`.

If the current platform's architecture is included in the `ARCHFLAGS`
(violating condition 3), cross-compilation will not be enabled, but the
`CMAKE_OSX_ARCHITECTURES` CMake option will still be set. (This is the case for
universal wheels.)

### Linux

Since `cibuildwheel` does not support cross-compilation on Linux,
`py-build-cmake` does not enable automatic cross-compilation for this platform.
By default, `cibuildwheel` will try to build your package in an emulated ARM64
container. This can be very slow, so it is recommended to use explicit
cross-compilation as described above.
