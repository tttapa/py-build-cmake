<small>[Index](index.html)</small>

# py-build-cmake configuration options

These options go in the `[tool.py-build-cmake]` section of the `pyproject.toml` configuration file.

## module
Defines the import name of the module or package, and the directory where it can be found. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `name` | Import name in Python (can be different from the name on PyPI, which is defined in the [project] section). | string | `/pyproject.toml/project/name` |
| `directory` | Directory containing the Python module/package.<br/>Relative to project directory. | path | `'.'` |

## editable
Defines how to perform an editable install (PEP 660). See https://tttapa.github.io/py-build-cmake/Editable-install.html for more information. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `mode` | Mechanism to use for editable installations. Either write a wrapper \_\_init\_\_.py file, install an import hook, or install symlinks to the original files. | `'wrapper'` \| `'hook'` \| `'symlink'` | `'wrapper'` |

## sdist
Specifies the files that should be included in the source distribution for this package. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `include` | Files and folders to include in the source distribution. May include the &#x27;\*&#x27; wildcard (but not &#x27;\*\*&#x27; for recursive patterns). | list | `[]` |
| `exclude` | Files and folders to exclude from the source distribution. May include the &#x27;\*&#x27; wildcard (but not &#x27;\*\*&#x27; for recursive patterns). | list | `[]` |

## cmake
Defines how to build the project to package. If omitted, py-build-cmake will produce a pure Python package. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `minimum_version` | Minimum required CMake version. If this version is not available in the system PATH, it will be installed automatically as a build dependency.<br/>For example: `minimum_version = "3.18"` | string | `none` |
| `build_type` | Build type passed to the configuration step, as `-DCMAKE_BUILD_TYPE=<?>`.<br/>For example: `build_type = "RelWithDebInfo"` | string | `none` |
| `config` | Configuration type passed to the build and install steps, as `--config <?>`. You can specify either a single string, or a list of strings. If a multi-config generator is used, all configurations in this list will be included in the package.<br/>For example: `config = ["Debug", "Release"]` | list | `build_type` |
| `preset` | CMake preset to use for configuration. Passed as `--preset <?>` during the configuration phase. | string | `none` |
| `build_presets` | CMake presets to use for building. Passed as `--preset <?>` during the build phase, once for each preset. | list | `preset` |
| `install_presets` | CMake presets to use for installing. Passed as `--preset <?>` during the installation phase, once for each preset. | list | `build_presets` |
| `generator` | CMake generator to use, passed to the configuration step, as `-G <?>`. If Ninja is used, and if it is not available in the system PATH, it will be installed automatically as a build dependency.<br/>For example: `generator = "Ninja Multi-Config"` | string | `none` |
| `source_path` | Folder containing CMakeLists.txt.<br/>Relative to project directory. | path | `'.'` |
| `build_path` | CMake build and cache folder.<br/>Absolute or relative to project directory. | path | `'.py-build-cmake_cache'` |
| `options` | Extra options passed to the configuration step, as `-D<option>=<value>`.<br/>For example: `options = {"WITH_FEATURE_X" = "On"}` | dict | `{}` |
| `args` | Extra arguments passed to the configuration step.<br/>For example: `args = ["--debug-find", "-Wdev"]` | list | `[]` |
| `find_python` | Specify hints for CMake&#x27;s FindPython module.<br/>For example: `find_python = true` | bool | `false` |
| `find_python3` | Specify hints for CMake&#x27;s FindPython3 module.<br/>For example: `find_python3 = false` | bool | `true` |
| `build_args` | Extra arguments passed to the build step.<br/>For example: `build_args = ["-j", "--target", "foo"]` | list | `[]` |
| `build_tool_args` | Extra arguments passed to the build tool in the build step (e.g. to Make or Ninja).<br/>For example: `build_tool_args = ["--verbose", "-d", "explain"]` | list | `[]` |
| `install_args` | Extra arguments passed to the install step.<br/>For example: `install_args = ["--strip"]` | list | `[]` |
| `install_components` | List of components to install, the install step is executed once for each component, with the option `--component <?>`.<br/>Use an empty string to specify the default component. | list | `['']` |
| `env` | Environment variables to set when running CMake. Supports variable expansion using `${VAR}` (but not `$VAR`).<br/>For example: `env = { "CMAKE_PREFIX_PATH" = "${HOME}/.local" }` | dict | `{}` |
| `pure_python` | Indicate that this package contains no platform-specific binaries, only Python scripts and other platform-agnostic files. It causes the Wheel tags to be set to `py3-none-any`.<br/>For example: `pure_python = true` | bool | `false` |
| `python_extension_abi` | Override the default ABI tag for the Wheel package.<br/>For packages with a Python extension module that make use of the full Python C API, this option should be set to `auto`.<br/>If your package does not contain Python extension modules (e.g. because it only includes executables to run as a subprocess, or only shared library files to be loaded using `ctypes`), you can set this to `none`.<br/>If your package only includes Python extension modules that use the CPython stable ABI, set this `abi3` (see also `abi3_minimum_cpython_version` below).<br/>For details about platform compatibility tags, see the PyPA specification: https://packaging.python.org/en/latest/specifications/platform-compatibility-tags<br/>For example: `python_extension_abi = 'none'` | `'auto'` \| `'none'` \| `'abi3'` | `'auto'` |
| `abi3_minimum_cpython_version` | If `python_extension_abi` is set to `abi3`, only use the stable CPython API for CPython version that are newer than `abi3_minimum_version`. Useful for nanobind, which supports the stable ABI for CPython 12 and later.<br/>The Python version is encoded as a single integer, consisting of the major and minor version numbers, without a dot.<br/>For example: `abi3_minimum_cpython_version = 312` | int | `32` |

## stubgen
If specified, mypy&#x27;s stubgen utility will be used to generate typed stubs for the Python files in the package. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `packages` | List of packages to generate stubs for, passed to stubgen as -p &lt;?&gt;. | list | `none` |
| `modules` | List of modules to generate stubs for, passed to stubgen as -m &lt;?&gt;. | list | `none` |
| `files` | List of files to generate stubs for, passed to stubgen without any flags. | list | `none` |
| `args` | List of extra arguments passed to stubgen. | list | `[]` |

## linux
Override options for Linux. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `editable` | Linux-specific editable options.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/editable` |  | `none` |
| `sdist` | Linux-specific sdist options.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/sdist` |  | `none` |
| `cmake` | Linux-specific CMake options.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/cmake` |  | `none` |

## windows
Override options for Windows. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `editable` | Windows-specific editable options.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/editable` |  | `none` |
| `sdist` | Windows-specific sdist options.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/sdist` |  | `none` |
| `cmake` | Windows-specific CMake options.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/cmake` |  | `none` |

## mac
Override options for Mac. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `editable` | Mac-specific editable options.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/editable` |  | `none` |
| `sdist` | Mac-specific sdist options.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/sdist` |  | `none` |
| `cmake` | Mac-specific CMake options.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/cmake` |  | `none` |

## cross
Causes py-build-cmake to cross-compile the project. See https://tttapa.github.io/py-build-cmake/Cross-compilation.html for more information. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `os` | Operating system configuration to inherit from. | `'linux'` \| `'mac'` \| `'windows'` | `none` |
| `implementation` | Identifier for the Python implementation.<br/>For details about platform compatibility tags, see the PyPA specification: https://packaging.python.org/en/latest/specifications/platform-compatibility-tags<br/>For example: `implementation = 'cp' # CPython` | string | `same as current interpreter` |
| `version` | Python version, major and minor, without dots.<br/>For details about platform compatibility tags, see the PyPA specification: https://packaging.python.org/en/latest/specifications/platform-compatibility-tags<br/>For example: `version = '310' # 3.10` | string | `same as current interpreter` |
| `abi` | Python ABI.<br/>For details about platform compatibility tags, see the PyPA specification: https://packaging.python.org/en/latest/specifications/platform-compatibility-tags<br/>For example: `abi = 'cp310'` | string | `same as current interpreter` |
| `arch` | Operating system and architecture (no dots or dashes, only underscores, all lowercase).<br/>For details about platform compatibility tags, see the PyPA specification: https://packaging.python.org/en/latest/specifications/platform-compatibility-tags<br/>For example: `arch = 'linux_x86_64'` | string | `same as current interpreter` |
| `prefix` | Root path of the Python installation. Used to set the `Python3_ROOT_DIR` CMake hint, see https://cmake.org/cmake/help/latest/module/FindPython3.html#hints.<br/>Absolute or relative to current configuration file. | path | `none` |
| `library` | Python library file (.so on Linux, .lib on Windows). Used to set the `Python3_LIBRARY` CMake artifact, see https://cmake.org/cmake/help/latest/module/FindPython3.html#artifacts-specification.<br/>Absolute or relative to current configuration file. | filepath | `none` |
| `include_dir` | Python include directory (containing Python.h). Used to set the `Python3_INCLUDE_DIR` CMake artifact, see https://cmake.org/cmake/help/latest/module/FindPython3.html#artifacts-specification.<br/>Absolute or relative to current configuration file. | path | `none` |
| `toolchain_file` | CMake toolchain file to use. See https://cmake.org/cmake/help/book/mastering-cmake/chapter/Cross%20Compiling%20With%20CMake.html for more information.<br/>Absolute or relative to current configuration file. | filepath | `none` |
| `copy_from_native_build` | If set, this will cause a native version of the CMake project to be built and installed in a temporary directory first, and the files in this list will be copied to the final cross-compiled package. This is useful if you need binary utilities that run on the build system while cross-compiling, or for things like stubs for extension modules that cannot be generated while cross-compiling.<br/>May include the &#x27;\*&#x27; wildcard (but not &#x27;\*\*&#x27; for recursive patterns). | list | `none` |
| `editable` | Override editable options when cross-compiling.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/editable` |  | `none` |
| `sdist` | Override sdist options when cross-compiling.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/sdist` |  | `none` |
| `cmake` | Override CMake options when cross-compiling.<br/>Inherits from: `/pyproject.toml/tool/py-build-cmake/cmake` |  | `none` |

# Local overrides

Additionally, two extra configuration files can be placed in the same directory as `pyproject.toml` to override some options for your specific use case:

- `py-build-cmake.local.toml`: the options in this file override the values in the `tool.py-build-cmake` section of `pyproject.toml`.<br/>This is useful if you need specific arguments or CMake options to compile the package on your system.
- `py-build-cmake.cross.toml`: the options in this file override the values in the `tool.py-build-cmake.cross` section of `pyproject.toml`.<br/>Useful for cross-compiling the package without having to edit the main configuration file.

# Command line overrides

Instead of using the `py-build-cmake.local.toml` and `py-build-cmake.cross.toml` files, you can also include additional config files using command line options:

- `--local`: specifies a toml file that overrides the `tool.py-build-cmake` section of `pyproject.toml`, similar to `py-build-cmake.local.toml`
- `--cross`: specifies a toml file that overrides the `tool.py-build-cmake.cross` section of `pyproject.toml`, similar to `py-build-cmake.cross.toml`

These command line overrides are applied after the `py-build-cmake.local.toml` and `py-build-cmake.cross.toml` files in the project folder (if any).

When using PyPA build, these flags can be specified using the `-C` or `--config-setting` flag: 
```sh
python -m build . -C--cross=/path/to/my-cross-config.toml
```
The same flag may appear multiple times, for example: 
```sh
python -m build . -C--local=conf-A.toml -C--local=conf-B.toml
```
For PyPA pip, you can use the `--config-settings` flag instead.
