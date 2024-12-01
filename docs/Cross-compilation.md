<small>[Index](index.html)</small>

# Cross-compilation

Cross-compiling Python extension modules is supported out of the box through
[CMake toolchain files](https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html).

When building packages using a tool like [`cibuildwheel`](https://github.com/pypa/cibuildwheel),
cross-compilation will also be enabled automatically whenever appropriate
(e.g. when building ARM64 packages on an Intel Mac).

> Table of contents  
> <span class="mono">¶</span>&emsp;[Terminology](#terminology)  
> <span class="mono">¶</span>&emsp;[Simple example](#simple-example)  
> &emsp;<small><span class="mono">¶</span>&emsp;[Caveats](#caveats)</small>  
> <span class="mono">¶</span>&emsp;[Complete cross-compilation workflow](#complete-cross-compilation-workflow)  
> &emsp;<small><span class="mono">¶</span>&emsp;[Set up the environment](#set-up-the-environment)</small>  
> &emsp;<small><span class="mono">¶</span>&emsp;[Download a cross-compilation toolchain for your _host_ system](#download-a-cross-compilation-toolchain-for-your-host-system)</small>  
> &emsp;<small><span class="mono">¶</span>&emsp;[Download Python for your _host_ system](#download-python-for-your-host-system)</small>  
> &emsp;<small><span class="mono">¶</span>&emsp;[Inspect and customize the toolchain files and py-build-cmake configuration](#inspect-and-customize-the-toolchain-files-and-py-build-cmake-configuration)</small>  
> &emsp;<small><span class="mono">¶</span>&emsp;[Cross-compile the pybind11-project example package using py-build-cmake](#cross-compile-the-pybind11-project-example-package-using-py-build-cmake)</small>  
> &emsp;<small><span class="mono">¶</span>&emsp;[Automated Bash scripts](#automated-bash-scripts)</small>  
> &emsp;<small><span class="mono">¶</span>&emsp;[A closer look at the CMake toolchain files](#a-closer-look-at-the-cmake-toolchain-files)</small>  
> &emsp;<small><span class="mono">¶</span>&emsp;[Cross-compilation of dependencies](#cross-compilation-of-dependencies)</small>  
> <span class="mono">¶</span>&emsp;[Automatic cross-compilation](#automatic-cross-compilation)  
> &emsp;<small><span class="mono">¶</span>&emsp;[Windows](#windows)</small>  
> &emsp;<small><span class="mono">¶</span>&emsp;[macOS](#macos)</small>  
> &emsp;<small><span class="mono">¶</span>&emsp;[Linux](#linux)</small>  

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
version = '312'        # 3.12
abi = 'cp312'          # (default ABI for CPython 3.12)
arch = 'linux_aarch64'
toolchain_file = 'aarch64-linux-gnu.cmake'
library = "/path-to-sysroot/usr/lib/aarch64-linux-gnu/libpython3.12.so"
include_dir = "/path-to-sysroot/usr/include/python3.12"
```
This will generate a package for CPython 3.12 on Linux for 64-bit ARM, using the
compilers defined by the toolchain file `aarch64-linux-gnu.cmake` (which you
should provide as well).

The format for the values in this file is the same as the format used for the
tags in wheel filenames, for example `pkg-1.2.3-cp312-cp312-linux_aarch64.whl`.
For details about platform compatibility tags, see the PyPA specification:
https://packaging.python.org/en/latest/specifications/platform-compatibility-tags.

### Caveats

Note that `py-build-cmake` does not check the Python version when
cross-compiling, so make sure that your CMakeLists.txt scripts find the correct
Python installation (one that matches the version, implementation, ABI,
operating system and architecture specified in the `py-build-cmake.cross.toml`
file), e.g. by setting the appropriate hints and artifacts variables:

- <https://cmake.org/cmake/help/latest/module/FindPython3.html#hints>
- <https://cmake.org/cmake/help/latest/module/FindPython3.html#artifacts-specification>

You can either specify these in your `py-build-cmake.cross.toml` configuration
as shown above, or in your CMake toolchain file.

---

## Complete cross-compilation workflow

This section will guide you through the full process of cross-compiling your
Python package.

You'll need the following:

- A cross-compilation toolchain that provides compilers for your _host_ system
  (while running on your _build_ system).
- A (pre-compiled) Python installation for the _host_ system.
- A py-build-cmake configuration file and a CMake toolchain file with the
  appropriate settings for your use case.

Let's go over these requirements step by step:

### Set up the environment

We'll first clone `py-build-cmake` and its example projects:

```sh
git clone https://github.com/tttapa/py-build-cmake --branch=0.3.0
cd py-build-cmake
```

### Download a cross-compilation toolchain for your _host_ system

It is important that the toolchain has an older version of glibc and the linux
headers, so that the resulting package is compatible with a wide range of
Linux distributions. The toolchains in your system's package manager are usually
not compatible with older systems.

You can find ready-to-use toolchains with good compatibility at https://github.com/tttapa/toolchains.

```sh
# Create a directory to save the cross-compilation toolchains into
mkdir -p toolchains
# Download and extract the toolchain for AArch64 (~121 MiB)
url="https://github.com/tttapa/toolchains/releases/download/1.0.1"
wget "$url/x-tools-aarch64-rpi3-linux-gnu-gcc14.tar.xz" -O- | tar xJ -C toolchains
# Verify that the toolchain works
./toolchains/x-tools/aarch64-rpi3-linux-gnu/bin/aarch64-rpi3-linux-gnu-gcc --version
```

### Download Python for your _host_ system

CMake needs to be able to locate the Python header files, and in some cases the
Python shared library before you can build your package.

You can download these from https://github.com/tttapa/python-dev.

```sh
# The toolchain is read-only by default, make it writable to add Python to it
chmod u+w "toolchains/x-tools/aarch64-rpi3-linux-gnu"
# Download and extract the Python binaries for AArch64 (~124 MiB)
url="https://github.com/tttapa/python-dev/releases/download/0.0.7"
wget "$url/python-dev-aarch64-rpi3-linux-gnu.tar.xz" -O- | tar xJ -C toolchains
```

### Inspect and customize the toolchain files and py-build-cmake configuration

The Python installations from https://github.com/tttapa/python-dev already
include the necessary CMake toolchain files and `py-build-cmake` configuration
files. Inspect them and customize to your specific setup if necessary.
(No changes necessary when just following this guide using the example projects).

```sh
# List the available CMake toolchain files.
ls toolchains/x-tools/*.cmake
# List the available py-build-cmake cross-compilation configuration files.
ls toolchains/x-tools/*.py-build-cmake.cross.toml
```

We'll have a quick look at the `toolchains/x-tools/aarch64-rpi3-linux-gnu.python3.11.py-build-cmake.cross.toml` as an example:

```toml
implementation = 'cp'
version = '311'
abi = 'cp311'
arch = 'manylinux_2_27_aarch64'
toolchain_file = 'aarch64-rpi3-linux-gnu.python.toolchain.cmake'

[cmake.options]
TOOLCHAIN_PYTHON_VERSION = '3.11'
```

The Python implementation, version, ABI and architecture were already discussed
in a previous section. The CMake toolchain file simply points to a file in the
same directory as the configuration file. We'll have a look at what it does
shortly. Finally, the `TOOLCHAIN_PYTHON_VERSION` variable tells the toolchain
file which version of Python to add to the CMake search paths.

### Cross-compile the pybind11-project example package using py-build-cmake

We now have our toolchain, the Python installation, and a configuration file
that selects the correct toolchain and Python version, so we are ready to
cross-compile our first package. We'll use the `pybind11-project` example that's
included with `py-build-cmake`.

```sh
# Install PyPA build as a build front-end
python3 -m pip install -U build
# Cross-compile the example package using our cross-compilation configuration
python3 -m build -w examples/pybind11-project \
    -C cross="$PWD/toolchains/x-tools/aarch64-rpi3-linux-gnu.python3.11.py-build-cmake.cross.toml"
```
If everything worked as expected, you should see output similar to the following.
```sh
-- The C compiler identification is GNU 14.2.0
-- The CXX compiler identification is GNU 14.2.0
-- Check for working C compiler: py-build-cmake/toolchains/x-tools/aarch64-rpi3-linux-gnu/bin/aarch64-rpi3-linux-gnu-gcc - skipped
[...]
-- Found Python3: py-build-cmake/toolchains/x-tools/aarch64-rpi3-linux-gnu/python3.11/usr/local/include/python3.11 (found version "3.11.10") found components: Development.Module
-- Detecting pybind11 CMake location
-- pybind11 CMake location: /tmp/build-env-xxxxx/lib/python3.9/site-packages/pybind11/share/cmake/pybind11
-- Performing Test HAS_FLTO
-- Performing Test HAS_FLTO - Success
-- Found pybind11: /tmp/build-env-xxxxx/lib/python3.9/site-packages/pybind11/include (found version "2.13.6")
-- Configuring done (1.4s)
-- Generating done (0.0s)
-- Build files have been written to: py-build-cmake/examples/pybind11-project/.py-build-cmake_cache/cp311-cp311-manylinux_2_27_aarch64
[ 50%] Building CXX object CMakeFiles/_add_module.dir/src/add_module.cpp.o
[100%] Linking CXX shared module _add_module.cpython-311-aarch64-linux-gnu.so
[100%] Built target _add_module
-- Installing: /tmp/xxxxx/staging/pybind11_project/_add_module.cpython-311-aarch64-linux-gnu.so
[...]
Successfully built pybind11_project-0.3.0-cp311-cp311-manylinux_2_27_aarch64.whl
```
You can see that CMake is using the cross-compiler we downloaded, and that it
managed to locate the version of Python we requested (CPython 3.11 for AArch64).
It is important to verify the module extension suffix
(`.cpython-311-aarch64-linux-gnu.so` in this case) and the Wheel tags
(`cp311-cp311-manylinux_2_27_aarch64`).

You can now copy the Wheel package in `examples/pybind11-project/dist/pybind11_project-0.3.0-cp311-cp311-manylinux_2_27_aarch64.whl`
to e.g. a Raspberry Pi and install it using `pip install`.

### Automated Bash scripts

The included `scripts/download-cross-toolchains-linux.sh` script downloads the
toolchains and Python installations for common architectures and current
versions of Python. You can then run the `examples/pybind11-project/cross-compile-linux.sh`
and `examples/nanobind-project/cross-compile-linux.sh` scripts to cross-compile
these example packages for this wide range of configurations.

```sh
./scripts/download-cross-toolchains-linux.sh
./examples/pybind11-project/cross-compile-linux.sh
./examples/nanobind-project/cross-compile-linux.sh
```
You can find the resulting Wheel packages in the
`examples/pybind11-project/dist` directory:
```sh
examples/pybind11-project/dist
├── pybind11_project-0.3.0-cp37-cp37m-linux_armv6l.whl
├── pybind11_project-0.3.0-cp37-cp37m-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-cp37-cp37m-manylinux_2_27_armv7l.whl
├── pybind11_project-0.3.0-cp37-cp37m-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-cp38-cp38-linux_armv6l.whl
├── pybind11_project-0.3.0-cp38-cp38-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-cp38-cp38-manylinux_2_27_armv7l.whl
├── pybind11_project-0.3.0-cp38-cp38-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-cp39-cp39-linux_armv6l.whl
├── pybind11_project-0.3.0-cp39-cp39-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-cp39-cp39-manylinux_2_27_armv7l.whl
├── pybind11_project-0.3.0-cp39-cp39-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-cp310-cp310-linux_armv6l.whl
├── pybind11_project-0.3.0-cp310-cp310-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-cp310-cp310-manylinux_2_27_armv7l.whl
├── pybind11_project-0.3.0-cp310-cp310-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-cp311-cp311-linux_armv6l.whl
├── pybind11_project-0.3.0-cp311-cp311-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-cp311-cp311-manylinux_2_27_armv7l.whl
├── pybind11_project-0.3.0-cp311-cp311-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-cp312-cp312-linux_armv6l.whl
├── pybind11_project-0.3.0-cp312-cp312-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-cp312-cp312-manylinux_2_27_armv7l.whl
├── pybind11_project-0.3.0-cp312-cp312-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-cp313-cp313-linux_armv6l.whl
├── pybind11_project-0.3.0-cp313-cp313-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-cp313-cp313-manylinux_2_27_armv7l.whl
├── pybind11_project-0.3.0-cp313-cp313-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-pp37-pypy37_pp73-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-pp37-pypy37_pp73-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-pp38-pypy38_pp73-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-pp38-pypy38_pp73-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-pp39-pypy39_pp73-manylinux_2_27_aarch64.whl
├── pybind11_project-0.3.0-pp39-pypy39_pp73-manylinux_2_27_x86_64.whl
├── pybind11_project-0.3.0-pp310-pypy310_pp73-manylinux_2_27_aarch64.whl
└── pybind11_project-0.3.0-pp310-pypy310_pp73-manylinux_2_27_x86_64.whl
```

### A closer look at the CMake toolchain files

Let us now look at `toolchains/x-tools/aarch64-rpi3-linux-gnu.python.toolchain.cmake`
more closely:
```cmake
include("${CMAKE_CURRENT_LIST_DIR}/aarch64-rpi3-linux-gnu.toolchain.cmake")

# [...]

# User options
set(TOOLCHAIN_PYTHON_VERSION "3" CACHE STRING "Python version to locate")
option(TOOLCHAIN_NO_FIND_PYTHON "Do not set the FindPython hints" Off)
option(TOOLCHAIN_NO_FIND_PYTHON3 "Do not set the FindPython3 hints" Off)

# [...]

# Internal variables
set(TOOLCHAIN_PYTHON_ROOT "${CMAKE_CURRENT_LIST_DIR}/${CROSS_GNU_TRIPLE}/python${TOOLCHAIN_PYTHON_VERSION}")
list(APPEND CMAKE_FIND_ROOT_PATH "${TOOLCHAIN_PYTHON_ROOT}")

# Determine the paths and other properties of the Python installation
function(toolchain_locate_python)
    # [...]
endfunction()

if (NOT TOOLCHAIN_NO_FIND_PYTHON OR NOT TOOLCHAIN_NO_FIND_PYTHON3)
    # [...]
    # Set FindPython hints and artifacts
    if (NOT TOOLCHAIN_NO_FIND_PYTHON)
        set(Python_ROOT_DIR ${TOOLCHAIN_PYTHON_ROOT_DIR} CACHE PATH "" FORCE)
        set(Python_LIBRARY ${TOOLCHAIN_PYTHON_LIBRARY} CACHE FILEPATH "" FORCE)
        set(Python_INCLUDE_DIR ${TOOLCHAIN_PYTHON_INCLUDE_DIR} CACHE PATH "" FORCE)
        set(Python_INTERPRETER_ID "Python" CACHE STRING "" FORCE)
    endif()
    # Set FindPytho3 hints and artifacts
    if (NOT TOOLCHAIN_NO_FIND_PYTHON3)
        set(Python3_ROOT_DIR ${TOOLCHAIN_PYTHON_ROOT_DIR} CACHE PATH "" FORCE)
        set(Python3_LIBRARY ${TOOLCHAIN_PYTHON_LIBRARY} CACHE FILEPATH "" FORCE)
        set(Python3_INCLUDE_DIR ${TOOLCHAIN_PYTHON_INCLUDE_DIR} CACHE PATH "" FORCE)
        set(Python3_INTERPRETER_ID "Python" CACHE STRING "" FORCE)
    endif()
    # Set pybind11 hints
    # [...]
    set(PYTHON_MODULE_DEBUG_POSTFIX ${PYTHON_MODULE_DEBUG_POSTFIX} CACHE INTERNAL "")
    set(PYTHON_MODULE_EXTENSION ${PYTHON_MODULE_EXTENSION} CACHE INTERNAL "")
    set(PYTHON_IS_DEBUG ${PYTHON_IS_DEBUG} CACHE INTERNAL "")
    # Set nanobind hints
    # [...]
    set(NB_SUFFIX ${NB_SUFFIX} CACHE INTERNAL "")
    set(NB_SUFFIX_S ${NB_SUFFIX_S} CACHE INTERNAL "")
endif()
```

First, it includes the standard toolchain file for the platform (the one that
sets the platform properties and compiler paths, see below).  
Next, it declares the options that you might want to configure as a user, such
as the version of Python to make available, and whether to set CMake's
[FindPython](https://cmake.org/cmake/help/latest/module/FindPython.html) and
[FindPython3](https://cmake.org/cmake/help/latest/module/FindPython3.html) hints.  
Then it adds the selected Python installation to CMake's search path, it
locates the Python library and include paths, its properties such as the
ABI and the extension suffix, and sets the FindPython hints.  
Finally, it sets some specific cache variables that are needed by the
[pybind11](https://github.com/pybind/pybind11) and [nanobind](https://github.com/wjakob/nanobind)
frameworks.

The file `toolchains/x-tools/aarch64-rpi3-linux-gnu.toolchain.cmake` contains:
```cmake
# System information
set(CMAKE_SYSTEM_NAME "Linux")
set(CMAKE_SYSTEM_PROCESSOR "aarch64")
set(CROSS_GNU_TRIPLE "aarch64-rpi3-linux-gnu"
    CACHE STRING "The GNU triple of the toolchain to use")
set(CMAKE_LIBRARY_ARCHITECTURE "aarch64-linux-gnu")

# Compiler flags
set(CMAKE_C_FLAGS_INIT       "-mcpu=cortex-a53+crc+simd")
set(CMAKE_CXX_FLAGS_INIT     "-mcpu=cortex-a53+crc+simd")
set(CMAKE_Fortran_FLAGS_INIT "-mcpu=cortex-a53+crc+simd")

# Search path configuration
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Packaging
set(CPACK_DEBIAN_PACKAGE_ARCHITECTURE "arm64")

# Compiler binaries
set(TOOLCHAIN_DIR "${CMAKE_CURRENT_LIST_DIR}/${CROSS_GNU_TRIPLE}")
set(CMAKE_C_COMPILER "${TOOLCHAIN_DIR}/bin/${CROSS_GNU_TRIPLE}-gcc"
    CACHE FILEPATH "C compiler")
set(CMAKE_CXX_COMPILER "${TOOLCHAIN_DIR}/bin/${CROSS_GNU_TRIPLE}-g++"
    CACHE FILEPATH "C++ compiler")
set(CMAKE_Fortran_COMPILER "${TOOLCHAIN_DIR}/bin/${CROSS_GNU_TRIPLE}-gfortran"
    CACHE FILEPATH "Fortran compiler")
```

### Cross-compilation of dependencies

If your Python package depends on native libraries, you'll have to cross-compile
these dependencies as well. You can either compile them from source yourself,
using the CMake toolchain files included with the toolchain, or you can use
the Conan package manager to build these dependencies for you. A Conan profile
is included as well, see e.g. `toolchains/x-tools/aarch64-rpi3-linux-gnu.profile.conan`.

---

## Automatic cross-compilation

In order to ensure compatibility with [`cibuildwheel`](https://github.com/pypa/cibuildwheel),
`py-build-cmake` automatically enables cross-compilation when certain
environment variables are set.

### Windows

Cross-compilation on Windows is enabled if the following conditions are met:

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

Cross-compilation on macOS is enabled if the following conditions are met:

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
cross-compilation as described [above](#complete-cross-compilation-workflow).
