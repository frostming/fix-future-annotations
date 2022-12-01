from __future__ import annotations
from typing import Union, List, Tuple


def foo() -> Union[int, str]:
    return 42


def add_to_list(x: List[str]) -> None:
    x.append("foo")


def bar(point: Tuple[int, int]) -> None:
    print(point)
