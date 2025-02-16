# Troubleshooting

## Verbose output and detailed information about the configuration and build process

You can enable py-build-cmake's verbose mode to make it print information about
the configuration, the exact subprocesses it invokes, the configure and build
environments, and so on.

When using a tool like PyPA `build` or `pip`, you can use the `-C` flag to pass
the `verbose` option:
```sh
python -m build . -C verbose
```

If you cannot easily change the command line options directly, you
can set the environment variable `PY_BUILD_CMAKE_VERBOSE`:
```sh
PY_BUILD_CMAKE_VERBOSE=1 pip install . -v # Linux/macOS
```
```sh
$Env:PY_BUILD_CMAKE_VERBOSE=1 # Windows
pip install . -v
Remove-Item Env:PY_BUILD_CMAKE_VERBOSE
```
Also note the `-v` flag to get pip to print the build output.

For [cibuildwheel](https://github.com/pypa/cibuildwheel), you can add the
following options to `pyproject.toml` to see all output from the build:
```toml
[tool.cibuildwheel]
build-verbosity = 1
environment = { PY_BUILD_CMAKE_VERBOSE="1" }
```

When inspecting the output, be aware that output of subprocesses is often much
higher up than the final error message or backtrace. For example, if you get an
error saying that the invocation of CMake failed, you'll have to scroll up to
see the actual CMake and compiler output.

## Performing a clean rebuild

To fully reconfigure and rebuild a project (e.g. after changing the CMake
generator, or after modifying environment variables like `CFLAGS` that affect
the initialization of CMake cache variables), simply remove py-build-cmake's
cache directory:
```sh
rm -r .py-build-cmake_cache
```
Note that this will also remove any editable installations of your project.

Often times, it is enough to simply delete the `CMakeCache.txt` file, without
performing a full rebuild:
```sh
# For a specific version and architecture (use tab completion):
rm .py-build-cmake_cache/cp311-cp311-linux_x86_64/CMakeCache.txt
# All versions and architectures:
rm .py-build-cmake_cache/*/CMakeCache.txt
```
Passing the `--fresh` flag to CMake has the same effect as manually deleting
`CMakeCache.txt`:
```sh
python -m build . -C o=cmake.args+='["--fresh"]'
```
