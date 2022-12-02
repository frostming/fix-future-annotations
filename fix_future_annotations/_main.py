from __future__ import annotations

import argparse
import ast
import difflib
import sys
from pathlib import Path

from tokenize_rt import reversed_enumerate, src_to_tokens, tokens_to_src

from fix_future_annotations._visitor import AnnotationVisitor


def _escaped(line: str) -> bool:
    return (len(line) - len(line.rstrip("\\"))) % 2 == 1


def _add_future_annotations(content: str) -> str:
    """Add from __future__ annotations after the first docstring and comments"""
    new_lines = ["from __future__ import annotations\n"]
    lines = content.splitlines(keepends=True)
    in_doc = False
    doc_quote = ""
    insert_pos = 0
    for i, line in enumerate(lines):
        if in_doc:
            code = line.split("#")[0].rstrip()
            if code.endswith(doc_quote) and not _escaped(code[: -len(doc_quote)]):
                in_doc = False
            continue
        line = line.lstrip()
        if line.startswith("#"):
            continue
        if line.startswith(('"""', 'r"""')):
            doc_quote = '"""'
            in_doc = True
        elif line.startswith(("'''", "r'''")):
            doc_quote = "'''"
            in_doc = True
        elif line.startswith(('r"', '"')):
            doc_quote = '"'
            in_doc = True
        elif line.startswith(("r'", "'")):
            doc_quote = "'"
            in_doc = True
        else:
            if insert_pos == 0:
                insert_pos = i
            if line.strip():
                break

        if in_doc:
            code = line.split("#")[0].rstrip()
            if (
                code.lstrip("r") != doc_quote
                and code.endswith(doc_quote)
                and not _escaped(code[: -len(doc_quote)])
            ):
                in_doc = False
    first_code = lines[i].lstrip()
    if not first_code.startswith("from __future__ import") and i == insert_pos:
        # Add a blank line after the future import
        new_lines.append("\n")
    lines[insert_pos:insert_pos] = new_lines
    return "".join(lines)


def fix_file(
    file_path: str | Path, write: bool = False, show_diff: bool = False
) -> bool:
    """Fix the file at file_path to use PEP 585, 604 and 563 syntax."""
    file_path = Path(file_path)
    file_content = file_path.read_text("utf-8")
    tokens = src_to_tokens(file_content)
    tree = ast.parse(file_content)
    visitor = AnnotationVisitor()
    token_funcs = visitor.get_token_functions(tree)
    for i, token in reversed_enumerate(tokens):
        if not token.src:
            continue
        for func in token_funcs.get(token.offset, []):
            func(i, tokens)

    new_content = tokens_to_src(tokens).lstrip()
    if visitor.need_future_annotations:
        new_content = _add_future_annotations(new_content)

    diff = list(
        difflib.unified_diff(
            file_content.splitlines(),
            new_content.splitlines(),
            fromfile="old",
            tofile="new",
        )
    )
    if diff:
        if show_diff:
            print(*diff, sep="\n")
        if write:
            print("Fixing file:", file_path)
            file_path.write_text(new_content, "utf-8")
        else:
            print("File needs to be fixed:", file_path)
    return bool(diff)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="+", help="File(s) to fix")
    parser.add_argument(
        "--check",
        "-c",
        dest="write",
        default=True,
        action="store_false",
        help="Only check the files without writing",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show diff details"
    )
    args = parser.parse_args(argv)
    diff_count = 0
    for filename in args.filenames:
        if filename.endswith(".py"):
            result = fix_file(filename, args.write, show_diff=args.verbose)
            diff_count += int(result)
    if diff_count:
        if args.write:
            message = f"All complete, {diff_count} files were fixed"
        else:
            message = f"All complete, {diff_count} files need to be fixed"
        print(message)
        sys.exit(1)
    else:
        print("All complete, no file is changed")
