<small>[Index](index.html)</small>

# py-build-cmake component build backend
The `py_build_cmake.build_component` build backend allows building packages containing additional binaries that are not included with the main distribution.

A possible use case is distributing debug symbols: these files can be large, and most users don't need them, so distributing them in a separate package makes sense.

You can find an example in the [alpaqa](https://pypi.org/project/alpaqa) package: <https://github.com/kul-optec/alpaqa/blob/main/python/alpaqa-debug/pyproject.toml>
## component
Options for a separately packaged component. 

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `main_project` | Directory containing the main pyproject.toml file.<br/>Relative to project directory. | path | `'..'` |
| `build_presets` | CMake presets to use for building. Passed as --preset &lt;?&gt; during the build phase, once for each preset. | list | `none` |
| `install_presets` | CMake presets to use for installing. Passed as --preset &lt;?&gt; during the installation phase, once for each preset. | list | `build_presets` |
| `build_args` | Extra arguments passed to the build step.<br/>For example: `build_args = ["-j"]` | list | `none` |
| `build_tool_args` | Extra arguments passed to the build tool in the build step (e.g. to Make or Ninja).<br/>For example: `build_tool_args = ["--verbose", "-d", "explain"]` | list | `none` |
| `install_args` | Extra arguments passed to the install step.<br/>For example: `install_args = ["--strip"]` | list | `none` |
| `install_components` | List of components to install, the install step is executed once for each component, with the option --component &lt;?&gt;. | list | `required` |
