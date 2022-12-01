import ctypes as typing
from ctypes import Union


def foo() -> typing.Union[str, int]:
    a: Union[str, int] = 1
    return a
