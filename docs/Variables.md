<small>[Index](index.html)</small>

# Variables

Below is a list of the CMake variables and environment variables that are set
by py-build-cmake during the build process.

| Variable | Description | Type |
|:---------|:------------|:----:|
| `PY_BUILD_CMAKE_VERSION` | The full version of py-build-cmake itself. This variable can be used to determine whether the package is being built by py-build-cmake or not. | CMake, Environment |
| `PY_BUILD_CMAKE_PROJECT_NAME` | The normalized name of the package being built (`[project.name]` in `pyproject.toml`). This name matches the eventual name of the Wheel file, and will be used for the `distinfo` directory inside of the Wheel. | CMake, Environment |
| `PY_BUILD_CMAKE_PROJECT_VERSION` | The full version of the package being built. | CMake, Environment |
| `PY_BUILD_CMAKE_IMPORT_NAME` | The import name of the top-level module or package of your project (`[tool.py-build-cmake.module.name]` in `pyproject.toml`). This can be used as the destination folder to install Python extension modules into. | CMake, Environment |
| `PY_BUILD_CMAKE_BINARY_DIR` | The CMake binary directory for the current build (note that there could be multiple build directories for a single package). | Environment |
| `PY_BUILD_CMAKE_INSTALL_PREFIX` | The CMake installation directory. Files that should be included in the Wheel package should be placed in this directory. In normal cases, you don't need to use this variable, because py-build-cmake sets the CMake `CMAKE_INSTALL_PREFIX` variable and invokes CMake with the correct `--prefix` option during installation. | Environment |
| `PY_BUILD_CMAKE_PYTHON_INTERPRETER` | Path to the Python interpreter that was used to invoke py-build-cmake ([`sys.executable`](https://docs.python.org/3/library/sys.html#sys.executable)). | CMake |
| `PY_BUILD_CMAKE_PYTHON_VERSION` | The full version of the Python interpreter that was used to invoke py-build-cmake ([`platform.python_version()`](https://docs.python.org/3/library/platform.html#platform.python_version)). Note that it includes any pre-release suffixes. | CMake |
| `PY_BUILD_CMAKE_PYTHON_VERSION_MAJOR` | Major version number of the Python interpreter that was used to invoke py-build-cmake ([`sys.version_info.major`](https://docs.python.org/3/library/sys.html#sys.version_info)). | CMake |
| `PY_BUILD_CMAKE_PYTHON_VERSION_MINOR` | Minor version number of the Python interpreter that was used to invoke py-build-cmake ([`sys.version_info.minor`](https://docs.python.org/3/library/sys.html#sys.version_info)). | CMake |
| `PY_BUILD_CMAKE_PYTHON_VERSION_PATCH` | Patch version number of the Python interpreter that was used to invoke py-build-cmake ([`sys.version_info.micro`](https://docs.python.org/3/library/sys.html#sys.version_info)). | CMake |
| `PY_BUILD_CMAKE_PYTHON_RELEASE_LEVEL` | Release level of the Python interpreter that was used to invoke py-build-cmake ([`sys.version_info.releaselevel`](https://docs.python.org/3/library/sys.html#sys.version_info)). | CMake |
| `PY_BUILD_CMAKE_ABIFLAGS` | The ABI flags of the Python interpreter that was used to invoke py-build-cmake ([`sys.abiflags`](https://docs.python.org/3/library/sys.html#sys.abiflags)). | CMake |
