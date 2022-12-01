"""this is a doc string"""
import typing as t

MyType = t.Union[str, int]


def foo() -> t.Tuple[t.Dict[str, int], t.Optional[str]]:
    pass


def bar() -> t.Union[int, str]:
    v: t.Optional[str] = "hahah"

    return v or 12134


def baz() -> t.Optional[
    int
]:
    return 42


def taf() -> t.Union[
    int, str, tuple
]:
    return 44
