from nanobind_project.sub_package import sub


def test_sub():
    assert sub(3, 2) == 1
