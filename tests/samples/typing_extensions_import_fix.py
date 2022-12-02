from __future__ import annotations

from typing_extensions import Literal


class Foo:
    @classmethod
    def create(cls, param: Literal["foo", "bar"]) -> Foo:
        pass
