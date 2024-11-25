from py_build_cmake.config.cli_override import CLIOption, parse_cli, parse_file


def test_parse_cli():

    assert parse_cli(
        r'tools.py-build-cmake.cmake."😄"-=[a, b, c, def, 551, False]'
    ) == CLIOption(
        action="-=",
        key=("tools", "py-build-cmake", "cmake", "😄"),
        value=["a", "b", "c", "def", 551, False],
    )
    assert parse_cli(r'"a b c\\\""=!') == CLIOption(
        action="=!",
        key=('a b c\\"',),
        value=None,
    )
    assert parse_cli(r'"a b c"=+ foo=5 ') == CLIOption(
        action="=+",
        key=("a b c",),
        value=" foo=5 ",
    )


def test_parse_file():
    file = r"""
            "a b c"    =+foo=5
            y= d, e, f# Comment
            z= a, b, c    # Comment
        tools.py-build-cmake.cmake."😄"-=[a, b, c, def, 551, False]
        a.b.c=!   # Comment
        bar  ={a = 1, b= 2, c =3, d=4, e=foo=5, f= foo=5, g = foo=5 }
        zed -=[]
        zed -=[1]
        zed -=[1, 2]   # Comment
        zed -=[1, 2,]
# Foo bar
        # Bar foo
        baz+=(path)$HOME/opt/python/bin
        """
    assert parse_file(file) == [
        CLIOption(action="=+", key=("a b c",), value="foo=5"),
        CLIOption(action="=", key=("y",), value=" d, e, f"),
        CLIOption(action="=", key=("z",), value=" a, b, c    "),
        CLIOption(
            action="-=",
            key=("tools", "py-build-cmake", "cmake", "😄"),
            value=["a", "b", "c", "def", 551, False],
        ),
        CLIOption(action="=!", key=("a", "b", "c"), value=None),
        CLIOption(
            action="=",
            key=("bar",),
            value={
                "a": 1,
                "b": 2,
                "c": 3,
                "d": 4,
                "e": "foo=5",
                "f": "foo=5",
                "g": "foo=5",
            },
        ),
        CLIOption(action="-=", key=("zed",), value=[]),
        CLIOption(action="-=", key=("zed",), value=[1]),
        CLIOption(action="-=", key=("zed",), value=[1, 2]),
        CLIOption(action="-=", key=("zed",), value=[1, 2]),
        CLIOption(action="+=(path)", key=("baz",), value="$HOME/opt/python/bin"),
    ]
