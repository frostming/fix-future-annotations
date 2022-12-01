import typing

MyType = typing.Union[str, int]


def foo() -> typing.Tuple[typing.Dict[str, int], typing.Optional[str]]:
    pass


def bar() -> typing.Union[int, str]:
    v: typing.Optional[str] = "hahah"

    return v or 12134


def baz() -> typing.Optional[
    int
]:
    return 42


def taf() -> typing.Union[
    int, str, tuple
]:
    return 44
