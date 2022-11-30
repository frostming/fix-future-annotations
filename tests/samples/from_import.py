from typing import Dict, Optional, Tuple, Union

MyType = Union[str, int]


def foo() -> Tuple[Dict[str, int], Optional[str]]:
    pass


def bar() -> Union[int, str]:
    v: Optional[str] = "hahah"

    return v or 12134


def baz() -> Optional[
    int
]:
    return 42


def taf() -> Union[
    int, str, tuple
]:
    return 44
