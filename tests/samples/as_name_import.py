import typing as t


def foo() -> t.Tuple[t.Dict[str, int], t.Optional[str]]:
    pass


def bar() -> t.Union[int, str]:
    v: t.Optional[str] = "hahah"
    return v or 12134
