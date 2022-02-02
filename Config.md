# py-build-cmake configuration options

These options go in the `[tool.py-build-cmake]` section.


## module
| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `name` | Import name in Python (can be different from the name on PyPI, which is defined in the [project] section). | string | `project.name` |
| `directory` | Directory containing the Python package. | path | `'.'` |
## sdist
| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `include` | Files and folders to include in the sdist distribution. May include the &#x27;*&#x27; wildcard (but not &#x27;**&#x27; for recursive patterns). | list | `[]` |
| `exclude` | Files and folders to exclude from the sdist distribution. May include the &#x27;*&#x27; wildcard (but not &#x27;**&#x27; for recursive patterns). | list | `[]` |
## cmake
| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `build_type` | Build type passed to the configuration step, as -DCMAKE_BUILD_TYPE=&lt;?&gt;.<br/>For example: build_type = &quot;RelWithDebInfo&quot; | string | `none` |
| `config` | Configuration type passed to the build and install steps, as --config &lt;?&gt;. | string | `tool.py-build-cmake.cmake.build_type` |
| `generator` | CMake generator to use, passed to the configuration step, as -G &lt;?&gt;. | string | `none` |
| `source_path` | Folder containing CMakeLists.txt. | path | `'.'` |
| `build_path` | CMake build and cache folder. | path | `'.py-build-cmake_cache'` |
| `options` | Extra options passed to the configuration step, as -D&lt;option&gt;=&lt;value&gt;.<br/>For example: options = {&quot;WITH_FEATURE_X&quot; = &quot;On&quot;} | dict | `{}` |
| `args` | Extra arguments passed to the configuration step.<br/>For example: args = [&quot;--debug-find&quot;, &quot;-Wdev&quot;] | list | `[]` |
| `build_args` | Extra arguments passed to the build step.<br/>For example: build_args = [&quot;-j&quot;] | list | `[]` |
| `build_tool_args` | Extra arguments passed to the build tool in the build step (e.g. to Make or Ninja).<br/>For example: build_tool_args = [&quot;VERBOSE=1&quot;] | list | `[]` |
| `install_args` | Extra arguments passed to the install step.<br/>For example: install_args = [&quot;--strip&quot;] | list | `[]` |
| `install_components` | List of components to install, the install step is executed once for each component, with the option --component &lt;?&gt;.<br/>Use an empty string to specify the default component. | list | `['']` |
| `env` | Environment variables to set when running CMake. | dict | `{}` |
| `linux` | Override options for Linux. | section | `none` |
| `windows` | Override options for Windows. | section | `none` |
| `mac` | Override options for Mac. | section | `none` |
## stubgen
| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `packages` | List of packages to generate stubs for, passed to stubgen as -p &lt;?&gt;. | list | `[]` |
| `modules` | List of modules to generate stubs for, passed to stubgen as -m &lt;?&gt;. | list | `[]` |
| `files` | List of files to generate stubs for, passed to stubgen without any flags. | list | `[]` |
| `args` | List of extra arguments passed to stubgen. | list | `[]` |
