# CMake FindPython

When building Python packages, it is crucial that CMake locates the appropriate
version of Python. To this end, py-build-cmake sets the necessary hints and
artifacts for CMake's [FindPython module](https://cmake.org/cmake/help/latest/module/FindPython3.html).

It is important to differentiate between Python installations for use during the
build process (e.g. for code generation) and Python installations that are
compatible with the target system that you'll be building for (e.g. the location
of `Python.h` when building extension modules).
Failure to keep these two kinds of Python installations separate may result in
build failures, or worse: packages that are silently broken or that are not
portable.

## Locating a Python interpreter to use during the build process

The first use case is invoking a Python interpreter to perform certain code
generation steps during the CMake build process. This is an interpreter that is
compatible with the _build_ system, and will usually be the same interpreter
that was used to invoke py-build-cmake.

To locate such an interpreter, look for the `Interpreter` component of the
FindPython module only:

```cmake
find_package(Python3 REQUIRED COMPONENTS Interpreter)
```
You can then use the Python executable during the build process using the
`Python3_EXECUTABLE` variable:
```
add_custom_command(
    OUTPUT "generated.cpp"
    COMMAND ${Python3_EXECUTABLE} codegen.py ...)
```

```{warning}
Do not use this Python interpreter for anything related to the target platform
that you're building for! There are no guarantees that the Python interpreter on
the _build_ system is compatible with the interpreter on the _target_ system
that your package will eventually be installed on. The interpreters may be
different versions of Python, different ABIs (e.g. free-threading,
debug/release), different implementations (e.g. CPython, PyPy, Pyodide), or even
entirely different architectures (when cross-compiling).  
If you find yourself querying the `sysconfig` or `platform` modules of
`Python3_EXECUTABLE` to make platform-specific decisions about the build
process, there's a good chance you're doing something wrong.
```

## Locating the Python development files for building extension modules

To build extension modules, you need to locate a Python installation for the
target system (the system where your package will eventually be installed).
The procedure here is slightly different depending on whether you're
cross-compiling or not:
- When performing a native build (no cross-compilation),
  it is recommended to always look for both the interpreter and the development
  components, to make sure that the development files are consistent with the
  interpreter that's creating the package.
- When cross-compiling, the interpreter is generally not usable, so you
  should look for the development files only. It is assumed that the user sets
  the necessary paths in `tool.py-build-cmake.cross`.

To handle these different situations, the following CMake snippet is recommended:
```cmake
if (CMAKE_CROSSCOMPILING AND NOT CMAKE_CROSSCOMPILING_EMULATOR)
    find_package(Python3 REQUIRED COMPONENTS Development.Module)
else()
    find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
endif()
```
If you're embedding a Python interpreter in your project instead of building
extension modules, you can use the `Development.Embed` component instead of
(or in addition to) `Development.Module`.

## Locating two Python interpreters

There may be cases where you need Python for code generation during the build
process _and_ where you need the Python development files for building extension
modules for the target system. If you need them in different subdirectories of
your CMake project (separated by `add_subdirectory`), you can simply use the
instructions from the previous sections (with one `find_package(Python3 ...)`
per directory, and without using the `GLOBAL` `find_package` flag).

If you need both interpreters in the same directory, things are a bit more
involved:
```cmake
# CMake 4.0 or later is required for this technique to work
cmake_minimum_required(VERSION 4.0)
# Look for the development files for the target first
if (CMAKE_CROSSCOMPILING AND NOT CMAKE_CROSSCOMPILING_EMULATOR)
    find_package(Python3 REQUIRED COMPONENTS Development.Module)
else()
    find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
endif()
# Then look for the interpreter for the build system,
# but return its variables using a different name
set(Python3_ARTIFACTS_PREFIX "_HOST")
find_package(Python3 REQUIRED COMPONENTS Interpreter)
```
You can then use the unqualified names (e.g. `Python3_add_library` or
`Python3::Module`) for building extension modules, and the names with the
`_HOST` prefix (e.g. `Python3_HOST_EXECUTABLE`) for code generation or other
uses during the build process.

If you set `Python3_ARTIFACTS_PREFIX` in your CMake script, you must inform
py-build-cmake of this change by setting the
`tool.py-build-cmake.cmake.find_python3_build_artifacts_prefix` option to
the same value as the `Python3_ARTIFACTS_PREFIX` that is used for locating the
Python interpreter. This ensures that the FindPython hints generated by
py-build-cmake also include the prefix.
