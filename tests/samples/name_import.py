from __future__ import annotations
import typing

def foo() -> tuple[dict[str, int], str | None]:
    pass

def bar() -> int | str:
    v: str | None = 'hahah'
    ab = 2
    return v or 12134

def baz():
    pass