# Component build backend configuration options

The `py_build_cmake.build_component` build backend allows building packages containing additional binaries that are not included with the main distribution.

A possible use case is distributing debug symbols: these files can be large, and most users don't need them, so distributing them in a separate package makes sense.

See [examples/minimal-debug-component](https://github.com/tttapa/py-build-cmake/tree/main/examples/minimal-debug-component) for more information.

The most important option is `main_project`, which is a relative path that points to the directory containing the`pyproject.toml` of the main package (where all CMake options are defined). Next, the options in the `component` section define which CMake projects and components should be installed in this component package.

## component
Options for a separately packaged component.

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| <a id="component.build_presets"></a> `build_presets` | CMake presets to use for building. Passed as `--preset <?>` during the build phase, once for each preset. | list | `none` |
| <a id="component.build_args"></a> `build_args` | Extra arguments passed to the build step.<br/>For example: `build_args = ["-j", "--target", "foo"]` | list+ | `none` |
| <a id="component.build_tool_args"></a> `build_tool_args` | Extra arguments passed to the build tool in the build step (e.g. to Make or Ninja).<br/>For example: `build_tool_args = ["--verbose", "-d", "explain"]` | list+ | `none` |
| <a id="component.install_only"></a> `install_only` | Do not build the project, only install it.<br/>For example: `install_only = true` | bool | `false` |
| <a id="component.install_args"></a> `install_args` | Extra arguments passed to the install step.<br/>For example: `install_args = ["--strip"]` | list+ | `none` |
| <a id="component.install_components"></a> `install_components` | List of components to install, the install step is executed once for each component, with the option `--component <?>`. | list | `required` |
