from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class Config:
    """Configuration for fix_future_annotations."""

    # The line patterns(regex) to exclude from the fix.
    exclude_lines: list[str] = field(default_factory=list)
    # The file patterns(regex) to exclude from the fix.
    exclude_files: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str | Path = "pyproject.toml") -> Config:
        """Load the configuration from a file."""
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except OSError:
            return cls()
        else:
            return cls(**data.get("tool", {}).get("fix_future_annotations", {}))

    def is_file_excluded(self, file_path: str) -> bool:
        return any(re.search(pattern, file_path) for pattern in self.exclude_files)

    def is_line_excluded(self, line: str) -> bool:
        return any(re.search(pattern, line) for pattern in self.exclude_lines)
