# Local configuration overrides

In addition to the main `pyproject.toml` file, two extra configuration files can be placed in the same directory as `pyproject.toml` to override some options for your specific use case:

- `py-build-cmake.local.toml`: the options in this file override the values in the `[tool.py-build-cmake]` section of `pyproject.toml`.<br/>This is useful if you need specific arguments or CMake options to compile the package on your system.
- `py-build-cmake.cross.toml`: the options in this file override the values in the `[tool.py-build-cmake.cross]` section of `pyproject.toml`.<br/>Useful for cross-compiling the package without having to edit the main configuration file.

It is recommended to exclude these files from version control, e.g. by adding them to your `.gitignore`.
