from __future__ import annotations

def foo() -> tuple[dict[str, int], str | None]:
    pass

def bar() -> int | str:
    v: str | None = 'hahah'
    return v or 12134