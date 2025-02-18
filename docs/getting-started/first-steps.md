# First Steps

This guide walks you through the basic py-build-cmake configuration for a
simple Python project with extension modules built using CMake.  
For a more detailed explanation of the project structure and the configuration
files, refer to the [Examples](<project:../examples/index.rst>), particularly
the **minimal example**. If you are looking for a more complete, real-world
example, have a look at <https://github.com/tttapa/py-build-cmake-example>.
It also contains proper dependency management using Conan, and uses
continuous integration workflows to test and deploy packages to the PyPI registry.

## Prerequisites

The following assumes that you already have a Python project that has a
pyproject.toml configuration file with the necessary metadata. If that's not the
case, please review <https://packaging.python.org/en/latest/guides/writing-pyproject-toml>
before continuing.

## Selecting py-build-cmake as the build backend

To use `py-build-cmake` as your Python build backend, add the following section to your `pyproject.toml` file:

```toml
[build-system]
requires = ["py-build-cmake~=0.4.3.dev0"]
build-backend = "py_build_cmake.build"
```

## Specifying the name of your Python package or module

If the import name of your package or module is different from the name in the
project metadata, you should specify the import name in the `module` section:

```toml
[tool.py-build-cmake.module]
name = "my_project"
```
A directory or Python file with this name should be available in the same
directory as the `pyproject.toml` file, or inside of a `src` directory
(recommended).

## Including the necessary files in the source distribution

Ensure that all files necessary for building your project from source are
included in the source distribution by adding the following section to `pyproject.toml`:

```toml
[tool.py-build-cmake.sdist]
include = ["CMakeLists.txt", "src/*.cpp"]
```
Add all required CMake files, C++ source and header files, etc. to the `include`
option.
The README and license files referenced in the project metadata, as well as the
Python files or folders that match the import name of your project will be
included automatically, so there's no need to add them here.

## Configuring CMake

To have `py-build-cmake` perform the standard CMake configure, build, and install
procedure in the project's root directory, define the following settings in `pyproject.toml`:

```toml
[tool.py-build-cmake.cmake]
minimum_version = "3.17"
build_type = "Release"
build_args = ["-j"]
```

For a complete list of configuration options, refer to the [Configuration reference](<project:../reference/config.md>).

## Adding installation rules to CMake

CMake needs to know where to place any Python extension modules, so make sure to
add the appropriate `install()` rules to your `CMakeLists.txt`. For example:

```cmake
# Find the Python development files
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
# Add the module to compile
Python3_add_library(_my_module MODULE "src/my_module.c" WITH_SOABI)
# Install the module
install(TARGETS _my_module
        DESTINATION ${PY_BUILD_CMAKE_IMPORT_NAME})
```

The destination path is relative to the root of the Wheel package. We used the
`PY_BUILD_CMAKE_IMPORT_NAME` variable to determine the package folder to install
the modules into. See <project:../reference/variables.md> for a list of other
useful variables that are set by `py-build-cmake`.

## Building and installing the project

Once the `pyproject.toml` configuration and the `CMakeLists.txt` script are
complete, you can build and install the project using `pip`:

```sh
pip install . -v
```

This command will compile the extension modules and install your project,
making it available for use within your Python environment.
