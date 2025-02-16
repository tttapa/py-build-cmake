# py-build-cmake

Documentation for [tttapa/py-build-cmake](https://github.com/tttapa/py-build-cmake),
a modern build backend for creating Python packages with extensions built using CMake.

## Features

::::{grid} 2 2 3 3
:gutter: 3

:::{grid-item-card} {fas}`cubes` Native packages
Create Python packages that use CMake to build performant C, C++ and Fortran extension modules.
:::

:::{grid-item-card} {fas}`edit` Declarative configuration
Standard `pyproject.toml` configuration file ([PEP 621](https://peps.python.org/pep-0621/))
for metadata and options.
:::

:::{grid-item-card} {fas}`laptop-code` Editable development installations
Editable installation ([PEP 660](https://peps.python.org/pep-0660/))
and automatic re-builds for effective development.
:::

:::{grid-item-card} {fas}`wand-magic-sparkles` Python bindings generation
Seamless integration with [pybind11](https://github.com/pybind/pybind11), [nanobind](https://github.com/wjakob/nanobind), and [SWIG](https://github.com/swig/swig), with stable ABI support.
:::

:::{grid-item-card} {fas}`sliders` Customizable CMake options
Configurable options for the configuration, compilation and installation of your
project.
:::

:::{grid-item-card} {fas}`wrench` Multi-configuration support
Install multiple CMake configurations and components, possibly accross
different Wheel packages.
:::

:::{grid-item-card} {fas}`cogs` First-class cross-compilation
Build for a wide range of platforms, including Raspberry Pi, Windows on ARM,
Intel and ARM64 macOS.
:::

:::{grid-item-card} {fas}`archive` Reproducible builds
[Reproducible builds](https://reproducible-builds.org/) for both source distributions and Wheel packages.
:::

:::{grid-item-card} {fas}`check-circle` Continuous integration
Simple continuous integration setup with [cibuildwheel](https://github.com/pypa/cibuildwheel)
for building and publishing packages.
:::

::::

<!-- :::{grid-item-card} {fas}`i-cursor` Stub generation
Automatic generation of `.pyi` stub files or type checking and autocompletion.
::: -->


***

```{toctree}
:maxdepth: 2
:glob:

getting-started/index.rst
usage/index.rst
reference/index.rst
examples/index.rst
```
