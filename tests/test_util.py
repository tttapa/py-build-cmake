from py_build_cmake.common.util import (
    python_version_int_to_py_limited_api_value,
    sysconfig_platform_to_conan_arch,
)


def test_python_version_int_to_py_limited_api_value():
    assert python_version_int_to_py_limited_api_value(32) == "0x03020000"
    assert python_version_int_to_py_limited_api_value(312) == "0x030C0000"


def test_sysconfig_platform_to_conan_arch():
    assert sysconfig_platform_to_conan_arch("win32") == "x86"
    assert sysconfig_platform_to_conan_arch("win-amd64") == "x86_64"
    assert sysconfig_platform_to_conan_arch("win-arm32") == "armv7"
    assert sysconfig_platform_to_conan_arch("win-arm64") == "armv8"
    assert sysconfig_platform_to_conan_arch("linux-i686") == "x86"
    assert sysconfig_platform_to_conan_arch("linux-x86_64") == "x86_64"
    assert sysconfig_platform_to_conan_arch("linux-armv6l") == "armv6"
    assert sysconfig_platform_to_conan_arch("linux-armv7l") == "armv7hf"
    assert sysconfig_platform_to_conan_arch("linux-aarch64") == "armv8"
    assert sysconfig_platform_to_conan_arch("emscripten-4.0.9-wasm32") == "wasm"
    assert sysconfig_platform_to_conan_arch("macosx-11.5-x86_64") == "x86_64"
    assert sysconfig_platform_to_conan_arch("macosx-11.5-arm64") == "armv8"
    assert sysconfig_platform_to_conan_arch("macosx-11.5-universal2") == "armv8|x86_64"


def test_platform_tag_to_conan_arch():
    assert sysconfig_platform_to_conan_arch("win32") == "x86"
    assert sysconfig_platform_to_conan_arch("win_amd64") == "x86_64"
    assert sysconfig_platform_to_conan_arch("win_arm32") == "armv7"
    assert sysconfig_platform_to_conan_arch("win_arm64") == "armv8"
    assert sysconfig_platform_to_conan_arch("linux_i686") == "x86"
    assert sysconfig_platform_to_conan_arch("linux_x86_64") == "x86_64"
    assert sysconfig_platform_to_conan_arch("linux_armv6l") == "armv6"
    assert sysconfig_platform_to_conan_arch("linux_armv7l") == "armv7hf"
    assert sysconfig_platform_to_conan_arch("linux_aarch64") == "armv8"
    assert sysconfig_platform_to_conan_arch("manylinux1_x86_64") == "x86_64"
    assert sysconfig_platform_to_conan_arch("manylinux1_aarch64") == "armv8"
    assert sysconfig_platform_to_conan_arch("manylinux_2_17_x86_64") == "x86_64"
    assert sysconfig_platform_to_conan_arch("manylinux_2_17_aarch64") == "armv8"
    assert sysconfig_platform_to_conan_arch("musllinux_x86_64") == "x86_64"
    assert sysconfig_platform_to_conan_arch("musllinux_aarch64") == "armv8"
    assert sysconfig_platform_to_conan_arch("pyodide_2024_0_wasm32") == "wasm"
    assert sysconfig_platform_to_conan_arch("macosx_11_5_x86_64") == "x86_64"
    assert sysconfig_platform_to_conan_arch("macosx_11_5_arm64") == "armv8"
    assert sysconfig_platform_to_conan_arch("macosx_11_5_universal2") == "armv8|x86_64"
    assert sysconfig_platform_to_conan_arch("macosx_11_5_foo") is None
