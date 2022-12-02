from __future__ import annotations

from tokenize_rt import Token, Offset
from ast import AST


def replace_name(i: int, tokens: list[Token], *, name: str, new: str) -> None:
    # Borrowed from
    # https://github.com/asottile/pyupgrade/blob/main/pyupgrade/_token_helpers.py#L461
    new_token = tokens[i]._replace(name="CODE", src=new)
    j = i
    while tokens[j].src != name:
        # timid: if we see a parenthesis here, skip it
        if tokens[j].src == ")":
            return
        j += 1
    tokens[i : j + 1] = [new_token]


def replace_string(i: int, tokens: list[Token], *, new: str) -> None:
    new_token = tokens[i]._replace(name="CODE", src=new)
    tokens[i] = new_token


def remove_name_from_import(i: int, tokens: list[Token], *, name: str) -> None:
    while tokens[i].src != name:
        i += 1
        if tokens[i].name == "NEWLINE":
            return
    j = i + 1
    while j < len(tokens) and tokens[j].name != "NEWLINE":
        if tokens[j].name == "UNIMPORTANT_WS":
            j += 1
            continue
        if tokens[j].src == ",":
            j += 1
            continue
        if tokens[j].src == "as":
            j += 1
            while j < len(tokens) and tokens[j].name != "NEWLINE":
                if tokens[j].name == "NAME":
                    j += 1
                    break
                j += 1
            continue
        break
    tokens[i:j] = []
    has_parenthesis = False
    j = i
    while j < len(tokens) and tokens[j].name != "NEWLINE":
        if tokens[j].src == ")":
            has_parenthesis = True
            break
        j += 1
    if not has_parenthesis:
        # we need to remove the last comma as well
        last_comma = -1
        while j >= 0 and tokens[j].name != "NAME":
            if tokens[j].src == ",":
                last_comma = j
            j -= 1
        if last_comma >= 0:
            del tokens[last_comma]


def remove_statement(i: int, tokens: list[Token]) -> None:
    j = i
    while j < len(tokens) and tokens[j].name != "NEWLINE":
        j += 1
    tokens[i : j + 1] = []


def ast_to_offset(ast: AST) -> Offset:
    return Offset(ast.lineno, ast.col_offset)


def find_token(tokens: list[Token], start: int, src: str) -> int:
    i = start
    while tokens[i].src != src:
        i += 1
    return i


def find_closing_bracket(tokens: list[Token], start: int) -> int:
    assert tokens[start].src == "[", tokens[start]
    i = start + 1
    depth = 1
    while depth:
        if tokens[i].src == "[":
            depth += 1
        elif tokens[i].src == "]":
            depth -= 1
        i += 1
    return i - 1
