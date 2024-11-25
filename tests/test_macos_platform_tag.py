from py_build_cmake.export.native_tags import _guess_platform_tag_mac as guess_tag


def test_parse_cli():
    test = lambda a, b: guess_tag({"ARCHFLAGS": a, "MACOSX_DEPLOYMENT_TARGET": b})
    assert test("-arch arm64", "10.15") == "macosx_11_0_arm64"
    assert test("-arch arm64", "11.7") == "macosx_11_7_arm64"
    assert test("-arch arm64", "12.3") == "macosx_12_3_arm64"
    assert test("-arch x86_64", "10.15") == "macosx_10_15_x86_64"
    assert test("-arch x86_64", "11.7") == "macosx_11_7_x86_64"
    assert test("-arch x86_64", "12.3") == "macosx_12_3_x86_64"
    assert test("-arch x86_64 -arch arm64", "10.15") == "macosx_10_15_universal2"
    assert test("-arch x86_64 -arch arm64", "11.7") == "macosx_11_7_universal2"
    assert test("-arch x86_64 -arch arm64", "12.3") == "macosx_12_3_universal2"
    assert test("-arch arm64 -arch x86_64", "10.15") == "macosx_10_15_universal2"
    assert test("-arch arm64 -arch x86_64", "11.7") == "macosx_11_7_universal2"
    assert test("-arch arm64 -arch x86_64", "12.3") == "macosx_12_3_universal2"
