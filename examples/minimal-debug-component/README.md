# Minimal debug component

Largely the same as the [minimal](../minimal) example, but uses
py-build-cmake's `build_component` backend to package the debugging symbols
in a separate, optional package.

Two main changes:
 1. Added a second [`pyproject.toml`](./debug/pyproject.toml) file that defines
    the package with the debugging symbols.
 2. Added a [`Debug.cmake`](./cmake/Debug.cmake) script with a function that
    strips the debugging symbols of the Python module (or any library) to a
    separate file. This function is then called from the main
    [`CMakeLists.txt`](./CMakeLists.txt).
