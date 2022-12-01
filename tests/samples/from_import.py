from __future__ import absolute_import

from typing import Union, Dict, Optional, Tuple  # this is a comment

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
