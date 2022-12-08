from typing import List, Optional, Tuple, Union


class NoFix:
    def __init__(self, names: List[str]) -> None:
        self.names = names

    def lengh(self) -> Optional[int]:
        if self.names:
            return len(self.names)
        return None


def foo() -> Union[str, int]:  # ffa: ignore
    return 42


def bar() -> Tuple[str, int]:
    return "bar", 42
