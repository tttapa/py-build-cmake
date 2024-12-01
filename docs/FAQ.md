<small>[Index](index.html)</small>

# Frequently asked questions

## Doesn't my project need a `setup.py` or `setup.cfg` file?

No, having a `pyproject.toml` file is enough.

The `setup.py` script and the `setup.cfg` file are specific to the
[`Setuptools`](https://setuptools.pypa.io/)
build backend. It is not needed for other build systems, such as
[`py-build-cmake`](https://github.com/tttapa/py-build-cmake),
[`Flit`](https://flit.pypa.io/en/latest/), [`Poetry`](https://python-poetry.org/)
etc.

Even when using Setuptools, it's best to avoid `setup.py` if you can, and to use
declarative configuration files like `setup.cfg` and `pyproject.toml` instead.  
From the [Setuptools quickstart guide](https://setuptools.pypa.io/en/latest/userguide/quickstart.html):

> The landscape of Python packaging is shifting and `Setuptools` has evolved to
> only provide backend support, no longer being the de-facto packaging tool in
> the market. Every python package must provide a `pyproject.toml` and specify
> the backend (build system) it wants to use. The distribution can then be
> generated with whatever tool that provides a `build sdist`-like functionality.
> While this may appear cumbersome, given the added pieces, it in fact
> tremendously enhances the portability of your package. The change is driven
> under [PEP 517](https://peps.python.org/pep-0517/#build-requirements).

> The `setup.py` file should be used only when custom scripting during the build
> is necessary. Examples are kept in this document to help people interested in
> maintaining or contributing to existing packages that use `setup.py`.
> Note that you can still keep most of configuration declarative in `setup.cfg`
> or `pyproject.toml` and use `setup.py` only for the parts not supported in
> those files (e.g. C extensions).

For more information about `setup.py` and Python packaging in general, see:
 - [Why you shouldn't invoke setup.py directly](https://blog.ganssle.io/articles/2021/10/setup-py-deprecated.html)
 - [Python Packaging User Guide](https://packaging.python.org/en/latest/)
 - [PEP 517](https://peps.python.org/pep-0517)
 - [pypa/setuptools: Eventually deprecate `setup.cfg` with automatic conversion to `pyproject.toml`](https://github.com/pypa/setuptools/issues/3214)

## The build fails. How can I find out what's going on?

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

## How can I perform a clean rebuild?

To fully reconfigure and rebuild a project (e.g. after changing the CMake
generator, or after modifying environment variables like `CFLAGS` that affect
the initialization of CMake cache variables), simply remove py-build-cmake's
cache directory:
```sh
rm -r .py-build-cmake_cache
```
Often times, it is enough to simply delete the `CMakeCache.txt` file, without
performing a full rebuild:
```sh
# For a specific version and architecture (use tab completion):
rm .py-build-cmake_cache/cp311-cp311-linux_x86_64/CMakeCache.txt
# All versions and architectures:
rm .py-build-cmake_cache/*/CMakeCache.txt
```

## How to upload my package to PyPI?

You'll have to upload a single source distribution, and one binary wheel for
each combination of Python version and platform you wish to support
(see next section).

For the actual upload of the packages to PyPI, it is highly recommended to use
trusted publishing:

- https://docs.pypi.org/trusted-publishers
- [pypa/gh-action-pypi-publish (GitHub Actions)](https://github.com/pypa/gh-action-pypi-publish)
- [Python Packaging User Guide: Uploading the distribution archives](https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-the-distribution-archives)
- https://twine.readthedocs.io/en/latest

## How to build my package for many Python versions, operating systems, and architectures?

In short: have a look at [py-build-cmake-example: .github/workflows](https://github.com/tttapa/py-build-cmake-example/tree/main/.github/workflows).

You can use a tool like [cibuildwheel](https://github.com/pypa/cibuildwheel) to
automate the build process for this large matrix of platform/version
combinations. Continuous integration providers like GitHub Actions also provide
job matrix capabilities. For example, the [py-build-cmake-example](https://github.com/tttapa/py-build-cmake-example/blob/24c5a0c4f796beedafd2d0a62134087a5be221d4/.github/workflows/wheels.yml#L107-L145)
project uses the following matrix to build the package for multiple
architectures and Python versions:

```yaml
  cross-build-linux:
    name: Cross-build wheels for ${{ matrix.host }} - ${{ matrix.python-version }}
    needs: [build-sdist]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        host: [x86_64-bionic-linux-gnu, aarch64-rpi3-linux-gnu, armv7-neon-linux-gnueabihf, armv6-rpi-linux-gnueabihf]
        python-version:
          - python3.7
          - python3.8
          - python3.9
          - python3.10
          - python3.11
          - python3.12
          - python3.13
          - pypy3.7-v7.3
          - pypy3.8-v7.3
          - pypy3.9-v7.3
          - pypy3.10-v7.3
        # PyPy does not provide 32-bit ARM binaries, so we exclude these:
        exclude:
          - python-version: pypy3.7-v7.3
            host: armv7-neon-linux-gnueabihf
          - python-version: pypy3.8-v7.3
            host: armv7-neon-linux-gnueabihf
          - python-version: pypy3.9-v7.3
            host: armv7-neon-linux-gnueabihf
          - python-version: pypy3.10-v7.3
            host: armv7-neon-linux-gnueabihf
          - python-version: pypy3.7-v7.3
            host: armv6-rpi-linux-gnueabihf
          - python-version: pypy3.8-v7.3
            host: armv6-rpi-linux-gnueabihf
          - python-version: pypy3.9-v7.3
            host: armv6-rpi-linux-gnueabihf
          - python-version: pypy3.10-v7.3
            host: armv6-rpi-linux-gnueabihf
```

The same workflow file also contains some steps to test the resulting wheels and
upload them to to PyPI. It's a good idea to check that the package version
matches the Git tag before uploading anything.

To build Universal Wheels for macOS (that work on both Intel- and ARM-based
machines), you can [set the following environment variables](https://github.com/pypa/cibuildwheel/blob/d018570bc4bdc792a1c7ba1e720d118686fa145b/cibuildwheel/macos.py#L250-L252):

```sh
export MACOSX_DEPLOYMENT_TARGET='10.14'
export _PYTHON_HOST_PLATFORM='macosx-10.14-universal2'
export ARCHFLAGS='-arch arm64 -arch x86_64'
```

To build packages for multiple architectures on Linux, I recommend [cross-compilation](./Cross-compilation.html).
This ensures that your package doesn't depend on any libraries (including GLIBC)
from the build server. You can use the modern GCC cross-compilers from
<https://github.com/tttapa/python-dev>, which also include pre-built
cross-compiled versions of Python.
