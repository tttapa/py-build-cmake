from cmake_preset import secret


def test_secret():
    assert secret == "secret-preset-value"
