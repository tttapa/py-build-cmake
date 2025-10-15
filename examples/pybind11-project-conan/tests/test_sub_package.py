from pybind11_project_conan.sub_package import sub


def test_sub():
    assert sub(3, 2) == 1
