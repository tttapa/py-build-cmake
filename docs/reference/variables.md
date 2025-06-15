# Variables

## Variables that are set by py-build-cmake

Below is a list of the CMake variables and environment variables that are set
by py-build-cmake during the build process.

### Variables about py-build-cmake itself

| Variable | Description | Type |
|:---------|:------------|:----:|
| <a id="PY_BUILD_CMAKE_VERSION"></a> `PY_BUILD_CMAKE_VERSION` | The full version of py-build-cmake itself. This variable can be used to determine whether the package is being built by py-build-cmake or not. | CMake, Environment |

### Variables about the project being built

| Variable | Description | Type |
|:---------|:------------|:----:|
| <a id="PY_BUILD_CMAKE_PROJECT_NAME"></a> `PY_BUILD_CMAKE_PROJECT_NAME` | The normalized name of the package being built (`[project.name]` in `pyproject.toml`). This name matches the eventual name of the Wheel file, and will be used for the `distinfo` directory inside of the Wheel. | CMake, Environment |
| <a id="PY_BUILD_CMAKE_PROJECT_VERSION"></a> `PY_BUILD_CMAKE_PROJECT_VERSION` | The full version of the package being built. | CMake, Environment |
| <a id="PY_BUILD_CMAKE_IMPORT_NAME"></a> `PY_BUILD_CMAKE_IMPORT_NAME` | The import name of the top-level module or package of your project (`[tool.py-build-cmake.module.name]` in `pyproject.toml`). This can be used as the destination folder to install Python extension modules into. | CMake, Environment |
| <a id="PY_BUILD_CMAKE_PACKAGE_PYTHON_TAG"></a> `PY_BUILD_CMAKE_PACKAGE_PYTHON_TAG` | The Python tag (https://packaging.python.org/en/latest/specifications/platform-compatibility-tags) for the package being built. Can be a CMake list, separated by semicolons. Possible values include `cp313`, `pp311`, `py3`, `py2;py3`. | CMake |
| <a id="PY_BUILD_CMAKE_PACKAGE_ABI_TAG"></a> `PY_BUILD_CMAKE_PACKAGE_ABI_TAG` | The ABI tag (https://packaging.python.org/en/latest/specifications/platform-compatibility-tags) for the package being built. Can be a CMake list, separated by semicolons. Possible values include `cp37m`, `cp313`, `cp313t`, `abi3`, `pypy311_pp73`, `none`. | CMake |
| <a id="PY_BUILD_CMAKE_PACKAGE_LIMITED_API"></a> `PY_BUILD_CMAKE_PACKAGE_LIMITED_API` | If the ABI tag is `abi3`, this variable contains the value for the `Py_LIMITED_API` macro that corresponds to the `abi3_minimum_cpython_version` option specified by the user. | CMake |
| <a id="PY_BUILD_CMAKE_PACKAGE_USE_SABI"></a> `PY_BUILD_CMAKE_PACKAGE_USE_SABI` | Similar to `PY_BUILD_CMAKE_PACKAGE_LIMITED_API`, but contains the limited API version in a format that can be passed to CMake's [`Python3_add_library`](https://cmake.org/cmake/help/latest/module/FindPython3.html#commands) `USE_SABI` option (e.g. `3.13`). | CMake |

### Variables about the current build environment

| Variable | Description | Type |
|:---------|:------------|:----:|
| <a id="PY_BUILD_CMAKE_BINARY_DIR"></a> `PY_BUILD_CMAKE_BINARY_DIR` | The CMake binary directory for the current build (note that there could be multiple build directories for a single package). | Environment |
| <a id="PY_BUILD_CMAKE_INSTALL_PREFIX"></a> `PY_BUILD_CMAKE_INSTALL_PREFIX` | The CMake installation directory. Files that should be included in the Wheel package should be placed in this directory. In normal cases, you don't need to use this variable, because py-build-cmake sets the CMake `CMAKE_INSTALL_PREFIX` variable and invokes CMake with the correct `--prefix` option during installation. | Environment |
| <a id="PY_BUILD_CMAKE_BUILD_PYTHON_INTERPRETER"></a> `PY_BUILD_CMAKE_BUILD_PYTHON_INTERPRETER` | Path to the Python interpreter that was used to invoke py-build-cmake ([`sys.executable`](https://docs.python.org/3/library/sys.html#sys.executable)). | CMake |
| <a id="PY_BUILD_CMAKE_BUILD_PYTHON_VERSION"></a> `PY_BUILD_CMAKE_BUILD_PYTHON_VERSION` | The full version of the Python interpreter that was used to invoke py-build-cmake ([`platform.python_version()`](https://docs.python.org/3/library/platform.html#platform.python_version)). Note that it includes any pre-release suffixes. | CMake |
| <a id="PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_MAJOR"></a> `PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_MAJOR` | Major version number of the Python interpreter that was used to invoke py-build-cmake ([`sys.version_info.major`](https://docs.python.org/3/library/sys.html#sys.version_info)). | CMake |
| <a id="PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_MINOR"></a> `PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_MINOR` | Minor version number of the Python interpreter that was used to invoke py-build-cmake ([`sys.version_info.minor`](https://docs.python.org/3/library/sys.html#sys.version_info)). | CMake |
| <a id="PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_PATCH"></a> `PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_PATCH` | Patch version number of the Python interpreter that was used to invoke py-build-cmake ([`sys.version_info.micro`](https://docs.python.org/3/library/sys.html#sys.version_info)). | CMake |
| <a id="PY_BUILD_CMAKE_BUILD_PYTHON_RELEASE_LEVEL"></a> `PY_BUILD_CMAKE_BUILD_PYTHON_RELEASE_LEVEL` | Release level of the Python interpreter that was used to invoke py-build-cmake ([`sys.version_info.releaselevel`](https://docs.python.org/3/library/sys.html#sys.version_info)). | CMake |
| <a id="PY_BUILD_CMAKE_BUILD_PYTHON_ABIFLAGS"></a> `PY_BUILD_CMAKE_BUILD_PYTHON_ABIFLAGS` | The ABI flags of the Python interpreter that was used to invoke py-build-cmake ([`sys.abiflags`](https://docs.python.org/3/library/sys.html#sys.abiflags)). | CMake |

```{warning}
When building extension modules, do not use the `PY_BUILD_CMAKE_BUILD_PYTHON_*`
variables to determine which Python library to link against. These variables
refer to the interpreter that was used to invoke py-build-cmake itself.
The _build_ Python interpreter pointed to by these variables may be different
from the _host_ Python interpreter (i.e. the interpreter that will eventually
be used to import the package). Using the incorrect Python interpreter will
cause issues when cross-compiling.
```

## Environment variables that affect the behavior of py-build-cmake

| Variable | Description |
|:---------|:------------|
| <a id="PY_BUILD_CMAKE_VERBOSE"></a> `PY_BUILD_CMAKE_VERBOSE` | Enables verbose mode: prints more information about the py-build-cmake configuration, options passed to CMake, etc. Equivalent to passing the `--verbose` config option. |
| <a id="PY_BUILD_CMAKE_VERBOSE_ENV"></a> `PY_BUILD_CMAKE_VERBOSE_ENV` | Enables printing of all environment variables in verbose mode. By default, most environment variables are censored to avoid accidentally leaking secrets, e.g. in a CI/CD log. Equivalent to passing the `--verbose-env` config option. |
| <a id="PY_BUILD_CMAKE_LOGLEVEL"></a> `PY_BUILD_CMAKE_LOGLEVEL` | Sets the level of the root logger. Can be used to silence all notifications or warnings. See <https://docs.python.org/3/library/logging.html#levels> for a list of valid levels. Equivalent to passing the `--loglevel` config option. |
| <a id="GITHUB_RUN_ATTEMPT"></a> `GITHUB_RUN_ATTEMPT` | If this value is greater than one, automatically enables verbose mode. Explicitly set `PY_BUILD_CMAKE_VERBOSE` to `false` to disable this behavior. |
| <a id="NO_COLOR"></a> `NO_COLOR` | Disables color output of the command line interface. |
| <a id="CLICOLOR_FORCE"></a> `CLICOLOR_FORCE` | Enable color output of the command line interface, even if not connected to a TTY. |
| <a id="_PYTHON_HOST_PLATFORM"></a> `_PYTHON_HOST_PLATFORM` | Overrides the Python platform tag used for Wheel filenames. Note that this only changes the tag, it does not actually affect the build process. |
| <a id="DIST_EXTRA_CONFIG"></a> `DIST_EXTRA_CONFIG` | On Windows, this variable can be set to the path of a configuration file that may contain the `build_ext.plat_name` and `build_ext.library_dirs` options. Support is limited to basic compatibility with cibuildwheel. See [Cross-compilation § Windows](https://tttapa.github.io/py-build-cmake/Cross-compilation.html#windows) for details. |
| <a id="ARCHFLAGS"></a> `ARCHFLAGS` | On macOS, this variable can be set to enable automatic cross-compilation or to build universal2 Wheels. Possible values: `-arch x86_64`, `-arch arm64` or `-arch x86_64 -arch arm64`. See [Cross-compilation § macOS](https://tttapa.github.io/py-build-cmake/Cross-compilation.html#macos) for details. Affects the platform tag of the generated Wheels, and passes the value on to CMake. |
| <a id="MACOSX_DEPLOYMENT_TARGET"></a> `MACOSX_DEPLOYMENT_TARGET` | Selects the macOS version to build for. Affects the platform tag of the generated Wheels, and passes the value on to CMake. Values should contain a major and minor version, separated by a dot. For example, `15.4`. |
| <a id="SOURCE_DATE_EPOCH"></a> `SOURCE_DATE_EPOCH` | Setting this to a Unix timestamp causes py-build-cmake to perform a [reproducible build](https://reproducible-builds.org/docs/source-date-epoch). The modification times of files in the generated sdist and Wheel archives are set to the given value. |

---

# Deprecated variables

| Deprecated variable | Recommended alternative |
|:--------------------|:------------------------|
| `PY_BUILD_CMAKE_PACKAGE_NAME` | `PY_BUILD_CMAKE_PROJECT_NAME` |
| `PY_BUILD_CMAKE_MODULE_NAME` | `PY_BUILD_CMAKE_IMPORT_NAME` |
| `PY_BUILD_CMAKE_PYTHON_INTERPRETER` | `PY_BUILD_CMAKE_BUILD_PYTHON_INTERPRETER` |
| `PY_BUILD_CMAKE_PYTHON_VERSION` | `PY_BUILD_CMAKE_BUILD_PYTHON_VERSION` |
| `PY_BUILD_CMAKE_PYTHON_VERSION_MAJOR` | `PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_MAJOR` |
| `PY_BUILD_CMAKE_PYTHON_VERSION_MINOR` | `PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_MINOR` |
| `PY_BUILD_CMAKE_PYTHON_VERSION_PATCH` | `PY_BUILD_CMAKE_BUILD_PYTHON_VERSION_PATCH` |
| `PY_BUILD_CMAKE_PYTHON_RELEASE_LEVEL` | `PY_BUILD_CMAKE_BUILD_PYTHON_RELEASE_LEVEL` |
| `PY_BUILD_CMAKE_PYTHON_ABIFLAGS` | `PY_BUILD_CMAKE_BUILD_PYTHON_ABIFLAGS` |
