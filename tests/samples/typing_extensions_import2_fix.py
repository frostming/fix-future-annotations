from __future__ import annotations

import typing_extensions as te


class Foo:
    @classmethod
    def create(cls, param: te.Literal["foo", "bar"]) -> Foo:
        pass
