from __future__ import annotations


def foo() -> int | str:
    return 42


def add_to_list(x: list[str]) -> None:
    x.append("foo")


def bar(point: tuple[int, int]) -> None:
    print(point)
