from __future__ import annotations

import argparse
import ast
import difflib
import sys
from pathlib import Path

from tokenize_rt import reversed_enumerate, src_to_tokens, tokens_to_src

from fix_future_annotations._visitor import AnnotationVisitor


def fix_file(file_path: str | Path, write: bool = False) -> bool:
    """Fix the file at file_path to use PEP 585, 604 and 563 syntax."""
    file_path = Path(file_path)
    file_content = file_path.read_text("utf-8")
    tokens = src_to_tokens(file_content)
    tree = ast.parse(file_content)
    visitor = AnnotationVisitor()
    visitor.visit(tree)
    for i, token in reversed_enumerate(tokens):
        if not token.src:
            continue
        for func in visitor.token_funcs[token.offset]:
            func(i, tokens)

    new_content = tokens_to_src(tokens).lstrip()
    if not visitor.need_future_annotations:
        new_content = f"from __future__ import annotations\n{new_content}"

    diff = list(
        difflib.unified_diff(
            file_content.splitlines(),
            new_content.splitlines(),
            fromfile="old",
            tofile="new",
        )
    )
    if diff:
        print("File changed:", file_path)
        print(*diff, sep="\n")
    if diff and write:
        file_path.write_text(new_content, "utf-8")
    return bool(diff)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="+", help="File(s) to fix")
    parser.add_argument(
        "--write", "-w", action="store_true", help="Write changes to the file"
    )
    args = parser.parse_args(argv)
    has_diff = False
    for filename in args.filenames:
        has_diff = has_diff or fix_file(filename, args.write)
    if has_diff:
        if args.write:
            message = "All complete, some files were fixed"
        else:
            message = "All complete, some files need to be fixed"
        print(message)
        sys.exit(1)
    else:
        print("All complete, no file is changed")
