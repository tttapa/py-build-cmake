# py-build-cmake configuration options

```text
List of py-build-cmake pyproject.toml options.

tool:

    py-build-cmake:

        module:

            name (string)
              Import name in Python (can be different from the name on PyPI,
              which is defined in the [project] section).
              Default: project.name

            directory (path)
              Directory containing the Python package.
              Default: '.'

        sdist:

            include (list)
              Files and folders to include in the sdist distribution. May
              include the '*' wildcard (but not '**' for recursive patterns).
              Default: []

            exclude (list)
              Files and folders to exclude from the sdist distribution. May
              include the '*' wildcard (but not '**' for recursive patterns).
              Default: []

        cmake:

            build_type (string)
              Build type passed to the configuration step, as
              -DCMAKE_BUILD_TYPE=<?>.
              For example: build_type = "RelWithDebInfo"
              Default: none

            config (string)
              Configuration type passed to the build and install steps, as
              --config <?>.
              Default: tool.py-build-cmake.cmake.build_type

            generator (string)
              CMake generator to use, passed to the configuration step, as -G
              <?>.
              Default: none

            source_path (path)
              Folder containing CMakeLists.txt.
              Default: '.'

            build_path (path)
              CMake build and cache folder.
              Default: '.py-build-cmake_cache'

            options (dict)
              Extra options passed to the configuration step, as
              -D<option>=<value>.
              For example: options = {"WITH_FEATURE_X" = "On"}
              Default: {}

            args (list)
              Extra arguments passed to the configuration step.
              For example: args = ["--debug-find", "-Wdev"]
              Default: []

            build_args (list)
              Extra arguments passed to the build step.
              For example: build_args = ["-j"]
              Default: []

            build_tool_args (list)
              Extra arguments passed to the build tool in the build step (e.g.
              to Make or Ninja).
              For example: build_tool_args = ["VERBOSE=1"]
              Default: []

            install_args (list)
              Extra arguments passed to the install step.
              For example: install_args = ["--strip"]
              Default: []

            install_components (list)
              List of components to install, the install step is executed once
              for each component, with the option --component <?>.
              Use an empty string to specify the default component.
              Default: ['']

            env (dict)
              Environment variables to set when running CMake.
              Default: {}

            linux (section)
              Override options for Linux.
              Default: none

            windows (section)
              Override options for Windows.
              Default: none

            mac (section)
              Override options for Mac.
              Default: none

        stubgen:

            packages (list)
              List of packages to generate stubs for, passed to stubgen as -p
              <?>.
              Default: []

            modules (list)
              List of modules to generate stubs for, passed to stubgen as -m
              <?>.
              Default: []

            files (list)
              List of files to generate stubs for, passed to stubgen without any
              flags.
              Default: []

            args (list)
              List of extra arguments passed to stubgen.
              Default: []

```
