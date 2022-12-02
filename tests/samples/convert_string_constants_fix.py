from __future__ import annotations

from typing import Literal


class Foo:
    @classmethod
    def create(cls, param: Literal["foo", "bar"]) -> Foo:
        pass
