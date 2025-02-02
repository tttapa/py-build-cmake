from py_build_cmake.common.platform import determine_build_platform_info


def _get_plat(archflags, version):
    env = {"ARCHFLAGS": archflags, "MACOSX_DEPLOYMENT_TARGET": version}
    plat = determine_build_platform_info(env, system="Darwin")
    return plat.platform_tag


def test_parse_cli():
    assert _get_plat("-arch arm64", "10.15") == "macosx_11_0_arm64"
    assert _get_plat("-arch arm64", "11.7") == "macosx_11_0_arm64"
    assert _get_plat("-arch arm64", "12.3") == "macosx_12_0_arm64"
    assert _get_plat("-arch x86_64", "10.15") == "macosx_10_15_x86_64"
    assert _get_plat("-arch x86_64", "11.7") == "macosx_11_0_x86_64"
    assert _get_plat("-arch x86_64", "12.3") == "macosx_12_0_x86_64"
    assert _get_plat("-arch x86_64 -arch arm64", "10.15") == "macosx_10_15_universal2"
    assert _get_plat("-arch x86_64 -arch arm64", "11.7") == "macosx_11_0_universal2"
    assert _get_plat("-arch x86_64 -arch arm64", "12.3") == "macosx_12_0_universal2"
    assert _get_plat("-arch arm64 -arch x86_64", "10.15") == "macosx_10_15_universal2"
    assert _get_plat("-arch arm64 -arch x86_64", "11.7") == "macosx_11_0_universal2"
    assert _get_plat("-arch arm64 -arch x86_64", "12.3") == "macosx_12_0_universal2"
