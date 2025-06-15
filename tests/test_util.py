from py_build_cmake.common.util import python_version_int_to_py_limited_api_value


def test_python_version_int_to_py_limited_api_value():
    assert python_version_int_to_py_limited_api_value(32) == "0x03020000"
    assert python_version_int_to_py_limited_api_value(312) == "0x030C0000"
