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

For more information about cross-compilation, ready-to-use toolchains, and 
example toolchain files, see <https://tttapa.github.io/Pages/Raspberry-Pi/C++-Development-Ubuntu>.

### Caveats

Note that `py-build-cmake` does not check the Python version, im ABI when
cross-compiling, so make sure that your CMakeLists.txt scripts find the correct
Python installation (on that matches the version, implementation, ABI, operating
system and architecture specified in the `py-build-cmake.cross.toml` file),
e.g. by setting the `-D Python3_ROOT_DIR:PATH="..."` CMake option (see
<https://cmake.org/cmake/help/latest/module/FindPython3.html#hints>).

## Advanced cross-builds

Some projects are more difficult to cross-compile, often for one of two reasons:

- The project first builds binaries that are themselves used later on in the 
  build process to build other files.
- Some parts of the build process require loading the previously built Python
  modules.

Since you cannot assume that the _build_ system can execute binaries for the _host_
system, or that _build_-Python can load modules compiled for _host_-Python, the only
solution is to build the project twice: once for the _build_ system, and once for
the _host_ system.

To get `py-build-cmake` to perform an initial _native_ build for the _build_
system before cross-compilation for th _host_ system, set the
`copy_from_native_build` option in the `py-build-cmake.cross.toml` file.  
The build process will then be as follows:

1. Configure the project for the _build_ system, with an additional CMake option
   `-D PY_BUILD_CMAKE_NATIVE_INSTALL_DIR:PATH="..."` that points to a temporary
   folder where the _build_ system's version of the project will be installed 
   in step (3).
2. Build the project for the _build_ system.
3. Install the project for the _build_ system into 
   `PY_BUILD_CMAKE_NATIVE_INSTALL_DIR`.
4. Configure the project for the _host_ system. The 
   `PY_BUILD_CMAKE_NATIVE_INSTALL_DIR` CMake option is included again, and 
   points to the same folder where step (3) installed the project for the _build_
   system. If you need executables for building, add this to the appropriate 
   CMake search paths in your CMakeLists.txt file. Cross-compilation is selected
   by setting the `-D CMAKE_TOOLCHAIN_FILE:FILEPATH="..."` CMake option.
5. Build the project for the _host_ system.
6. Install the project for the _host_ system into a staging directory (different
   from `PY_BUILD_CMAKE_NATIVE_INSTALL_DIR`).
7. If any patterns were specified using the `copy_from_native_build` option,
   match these against the files in `PY_BUILD_CMAKE_NATIVE_INSTALL_DIR`, and 
   move the matching files from `PY_BUILD_CMAKE_NATIVE_INSTALL_DIR` to the 
   staging directory, to be included in the package.

The last step provides a convenient way to install stubs when cross-compiling:
generating stubs requires loading the compiled extension modules, so cannot be
done for _host_ modules on the _build_ system. Instead, the stubs are generated
from the _build_ modules in step (2), and then copied into the _host_ package in
step (7).

### Caveats

Be careful not to copy any incompatible binaries from the _native_ build
into the _host_ package.
