#!/usr/bin/env bash

# This script cross-compiles the Python package for a range of popular
# architectures (x86-64, ARMv6, ARMv7, ARMv8-64) and all current versions of
# CPython and PyPy.
#
# You should first download the cross-compilation toolchains
# (https://github.com/tttapa/toolchains) and the Python libraries for the given
# architecture (https://github.com/tttapa/python-dev). This is done by running
# the ../../scripts/download-cross-toolchains-linux.sh script.
#
# These toolchains include CMake toolchain files and configuration files for
# py-build-cmake ({triple}.{python_version}.py-build-cmake cross.toml). When
# these configuration files are passed using the -C cross flag, it will
# cause py-build-cmake to cross-compile the package for the given architecture
# and Python version (which may be different from the architecture and version
# of the Python interpreter that is used to drive the build process).
#
# The resulting Python Wheel packages can be found in the dist directory.
#
# See https://tttapa.github.io/py-build-cmake/Cross-compilation.html for more
# information about cross-compilation.

cd "$(dirname "${BASH_SOURCE[0]}")"

# Select the architectures and Python versions to build for.
triples=(x86_64-bionic-linux-gnu armv6-rpi-linux-gnueabihf armv7-neon-linux-gnueabihf aarch64-rpi3-linux-gnu)
python_versions=("python3.7" "python3.8" "python3.9" "python3.10" "python3.11" "python3.12" "python3.13")
pypy_triples=(x86_64-bionic-linux-gnu aarch64-rpi3-linux-gnu)
pypy_versions=("pypy3.7-v7.3" "pypy3.8-v7.3" "pypy3.9-v7.3" "pypy3.10-v7.3")

# Ensure that the necessary toolchains are available.
toolchain_folder="$PWD/../../toolchains"
if [ ! -d "$toolchain_folder/x-tools" ]; then
    echo "Cross-compilation toolchains not found."
    echo "Please run \"$(realpath "$PWD/../../scripts/download-cross-toolchains-linux.sh")\" first."
    exit 1
fi

set -ex

# Install PyPA build
python3 -m pip install --quiet --no-warn-script-location -U pip build

# Link the C++ standard library statically to support systems that have an
# older version installed. Same for the GCC runtime library (libgcc).
export LDFLAGS="-static-libgcc -static-libstdc++"

# Cross-compile the package for CPython.
for triple in ${triples[@]}; do
    for python_version in ${python_versions[@]}; do
        rm -rf .py-build-cmake_cache
        python3 -m build . -w \
            -C cross="$toolchain_folder/x-tools/$triple.$python_version.py-build-cmake.cross.toml"
    done
done

# Cross-compile the package for PyPy.
for triple in ${pypy_triples[@]}; do
    for python_version in ${pypy_versions[@]}; do
        rm -rf .py-build-cmake_cache
        python3 -m build . -w \
            -C cross="$toolchain_folder/x-tools/$triple.$python_version.py-build-cmake.cross.toml"
    done
done
