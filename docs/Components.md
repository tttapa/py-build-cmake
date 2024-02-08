<small>[Index](index.html)</small>

# py-build-cmake component build backend
The `py_build_cmake.build_component` build backend allows building packages containing additional binaries that are not included with the main distribution.

A possible use case is distributing debug symbols: these files can be large, and most users don't need them, so distributing them in a separate package makes sense.

See [examples/minimal-debug-component](https://github.com/tttapa/py-build-cmake/tree/main/examples/minimal-debug-component) for more information.

## component
Options for a separately packaged component. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `main_project` | Directory containing the main pyproject.toml file.<br/>Relative to project directory. | path | `'..'` |
| `build_args` | Extra arguments passed to the build step.<br/>For example: `build_args = ["-j", "--target", "foo"]` | list+ | `none` |
| `build_tool_args` | Extra arguments passed to the build tool in the build step (e.g. to Make or Ninja).<br/>For example: `build_tool_args = ["--verbose", "-d", "explain"]` | list+ | `none` |
| `install_only` | Do not build the project, only install it.<br/>For example: `install_only = true` | bool | `false` |
| `install_args` | Extra arguments passed to the install step.<br/>For example: `install_args = ["--strip"]` | list+ | `none` |
| `install_components` | List of components to install, the install step is executed once for each component, with the option `--component <?>`. | list | `required` |

