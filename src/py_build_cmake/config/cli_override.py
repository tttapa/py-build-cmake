from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, cast

from lark import Lark, Token, Transformer, v_args

grammar = Path(__file__).with_suffix(".lark").read_text()


@dataclass
class CLIOption:
    action: str
    key: tuple[str, ...]
    value: bool | str | list | dict | float | None


class TreeToCLIOption(Transformer):
    @v_args(inline=True)
    def escaped_string(self, s: Token):
        return s[1:-1].encode("raw_unicode_escape").decode("unicode_escape")

    @v_args(inline=True)
    def unquoted_string(self, s: Token):
        return s.value

    @v_args(inline=True)
    def full(self, k, a, v=None):
        return CLIOption(a.value, k, v)

    lines = list
    keys = tuple

    array = list
    pair = tuple
    object = dict

    NUMBER = int
    TRUE = lambda self, _: True
    FALSE = lambda self, _: False


cli_parser = Lark(grammar, start="option", parser="lalr", transformer=TreeToCLIOption())
file_parser = Lark(grammar, start="lines", parser="lalr", transformer=TreeToCLIOption())


def parse_cli(s: str) -> CLIOption:
    return cast(CLIOption, cli_parser.parse(s))


def parse_file(s: str) -> list[CLIOption]:
    return cast(List[CLIOption], file_parser.parse(s))
