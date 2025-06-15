# Command-line overrides

Instead of using the `py-build-cmake.local.toml` and `py-build-cmake.cross.toml` files, you can also include additional config files using command-line options:

- `--local`: specifies a toml file that overrides the `tool.py-build-cmake` section of `pyproject.toml`, similar to `py-build-cmake.local.toml`
- `--cross`: specifies a toml file that overrides the `tool.py-build-cmake.cross` section of `pyproject.toml`, similar to `py-build-cmake.cross.toml`

These command-line overrides are applied after the `py-build-cmake.local.toml` and `py-build-cmake.cross.toml` files in the project folder (if any).

When using PyPA build, these flags can be specified using the `-C` or `--config-setting` flag:
```sh
python -m build . -C--cross=/path/to/my-cross-config.toml
```
The same flag may appear multiple times. The order for the same flag is preserved, but all `--cross` flags are applied after all `--local` flags. For example:
```sh
python -m build . -C--local=conf-A.toml -C--local=conf-B.toml
```
For PyPA pip, you can use the `-C` or `--config-settings` flags instead.

Finally, you can also specify overrides for specific configuration options on the command-line, for example:
```sh
python -m build . \
   -C override=cmake.options.CMAKE_PREFIX_PATH+="/opt/some-package" \
   -C override=cmake.env.PATH=+(path)"/opt/some-package/bin"
```
The format consists of the configuration option keys (separated) by periods, followed by an operator (such as `+=`, see below), followed by the value.

The following operators are supported:
- `=`: Sets the configuration option regardless of its previous value.
- `+=`: Appends the given value to the previous value.
- `=+`: Prepends the given value to the previous value.
- `=-`: Removes the given value from the previous value.
- `=!`: Clears the configuration option if set.
- `+=(path)`: Appends the given value to the previous value, joining them with the system's path separator (`:` on Unix, `;` on Windows).
- `=+(path)`: Prepends the given value to the previous value, joining them with the system's path separator.

Values can be specified using a TOML-like syntax, using square brackets for lists, and curly braces with equal signs for dictionaries. Simple strings can be specified without quotes, but quotes are required when including special characters. Note the escaping of quotes to prevent the shell from stripping them out.
```sh
python -m build . \
   -C "override=cmake.options.CMAKE_PREFIX_PATH=[\"/opt/some-package\", \"/another\"]" \
   -C "override=cmake.env+={MY_PATH = \"/opt/some-package\" }" \
   -C "override=cmake.find_python=true"
```
