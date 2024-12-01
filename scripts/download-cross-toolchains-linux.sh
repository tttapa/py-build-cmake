#!/usr/bin/env bash

# This script downloads cross-compilation toolchains for a range of popular
# architectures (x86-64, ARMv6, ARMv7, ARMv8-64), as well as binaries of all
# current versions of CPython and PyPy.
# These can then be used to cross-compile packages using py-build-cmake

cd "$( dirname "${BASH_SOURCE[0]}" )"/..

triples=(x86_64-bionic-linux-gnu armv6-rpi-linux-gnueabihf armv7-neon-linux-gnueabihf aarch64-rpi3-linux-gnu)
gcc_version="14"
toolchain_version="1.0.1"
python_dev_version="0.0.7"
toolchain_folder="$PWD/toolchains"

set -ex

mkdir -p "$toolchain_folder/x-tools"
for triple in ${triples[@]}; do
    chmod u+w "$toolchain_folder/x-tools"
    if [ ! -d "$toolchain_folder/x-tools/$triple" ]; then
        url=https://github.com/tttapa/toolchains/releases/download/$toolchain_version
        wget "$url/x-tools-$triple-gcc$gcc_version.tar.xz" -O- | tar xJ -C "$toolchain_folder"
    fi
    chmod u+w "$toolchain_folder/x-tools/$triple"
    if [ ! -d "$toolchain_folder/x-tools/$triple/python" ]; then
        url=https://github.com/tttapa/python-dev/releases/download
        wget "$url/$python_dev_version/python-dev-$triple.tar.xz" -O- | tar xJ -C "$toolchain_folder"
    fi
done

# To delete the toolchains again, use
#   chmod -R u+w toolchains && rm -rf toolchains
