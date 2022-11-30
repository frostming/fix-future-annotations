from __future__ import annotations

import ast
import contextlib
import sys
from collections import defaultdict
from functools import partial
from typing import Any, Callable

from tokenize_rt import NON_CODING_TOKENS, Offset, Token

from fix_future_annotations.utils import (
    ast_to_offset,
    find_closing_bracket,
    find_token,
    remove_name_from_import,
    remove_statement,
    replace_name,
)

BASIC_COLLECTION_TYPES = {"Set", "List", "Tuple", "Dict", "FrozenSet", "Type"}
IMPORTS_TO_REMOVE = BASIC_COLLECTION_TYPES | {"Optional", "Union"}
TokenFunc = Callable[[int, list[Token]], None]


def _fix_optional(i: int, tokens: list[Token]) -> None:
    j = find_token(tokens, i, "[")
    k = find_closing_bracket(tokens, j)
    if tokens[j].line == tokens[k].line:
        tokens[k] = Token("CODE", " | None")
        del tokens[i : j + 1]
    else:
        tokens[j] = tokens[j]._replace(src="(")
        tokens[k] = tokens[k]._replace(src=")")
        tokens[i:j] = [Token("CODE", "None | ")]


def _get_arg_count(node_slice: ast.expr) -> int:
    if sys.version_info < (3, 9) and isinstance(node_slice, ast.Index):
        node_slice = node_slice.value

    if isinstance(node_slice, ast.Slice):  # not a valid annotation
        return

    if isinstance(node_slice, ast.Tuple):
        if node_slice.elts:
            return len(node_slice.elts)
        else:
            return 0  # empty Union
    else:
        return 1


def _fix_union(i: int, tokens: list[Token], *, arg_count: int) -> None:
    depth = 1
    parens_done = []
    open_parens = []
    commas = []
    coding_depth = None

    j = find_token(tokens, i, "[")
    k = j + 1
    while depth:
        # it's possible our first coding token is a close paren
        # so make sure this is separate from the if chain below
        if (
            tokens[k].name not in NON_CODING_TOKENS
            and tokens[k].src != "("
            and coding_depth is None
        ):
            if tokens[k].src == ")":  # the coding token was an empty tuple
                coding_depth = depth - 1
            else:
                coding_depth = depth

        if tokens[k].src in "([{":
            if tokens[k].src == "(":
                open_parens.append((depth, k))

            depth += 1
        elif tokens[k].src in ")]}":
            if tokens[k].src == ")":
                paren_depth, open_paren = open_parens.pop()
                parens_done.append((paren_depth, (open_paren, k)))

            depth -= 1
        elif tokens[k].src == ",":
            commas.append((depth, k))

        k += 1
    k -= 1

    assert coding_depth is not None
    assert not open_parens, open_parens
    comma_depth = min((depth for depth, _ in commas), default=sys.maxsize)
    min_depth = min(comma_depth, coding_depth)

    to_delete = [
        paren
        for depth, positions in parens_done
        if depth < min_depth
        for paren in positions
    ]

    if comma_depth <= coding_depth:
        comma_positions = [k for depth, k in commas if depth == comma_depth]
        if len(comma_positions) == arg_count:
            to_delete.append(comma_positions.pop())
    else:
        comma_positions = []

    to_delete.sort()

    if tokens[j].line == tokens[k].line:
        del tokens[k]
        for comma in comma_positions:
            tokens[comma] = Token("CODE", " |")
        for paren in reversed(to_delete):
            del tokens[paren]
        del tokens[i : j + 1]
    else:
        tokens[j] = tokens[j]._replace(src="(")
        tokens[k] = tokens[k]._replace(src=")")

        for comma in comma_positions:
            tokens[comma] = Token("CODE", " |")
        for paren in reversed(to_delete):
            del tokens[paren]
        del tokens[i:j]


class AnnotationVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self._has_future_annotations = False
        self._modified = False
        self.typing_import_name = "typing"
        self._in_annotation_stack: list[bool] = [False]
        self._typing_imports: dict[str, str] = {}
        self.token_funcs: dict[Offset, list[TokenFunc]] = defaultdict(list)

    def add_token_func(self, offset: Offset, func: TokenFunc) -> None:
        self.token_funcs[offset].append(func)
        self._modified = True

    @property
    def in_annotation(self) -> bool:
        return self._in_annotation_stack[-1]

    @property
    def need_future_annotations(self) -> bool:
        return not self._has_future_annotations and self._modified

    @contextlib.contextmanager
    def visit_annotation(self) -> None:
        self._in_annotation_stack.append(True)
        try:
            yield
        finally:
            self._in_annotation_stack.pop()

    def generic_visit(self, node: ast.AST) -> Any:
        for field in reversed(node._fields):
            value = getattr(node, field)
            if field in {"annotation", "returns"}:
                ctx = self.visit_annotation()
            else:
                ctx = contextlib.nullcontext()
            with ctx:
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            self.visit(item)
                elif isinstance(value, ast.AST):
                    self.visit(value)

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            if alias.name == "typing":
                self.typing_import_name = alias.asname or "typing"
        return self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        if node.module == "__future__":
            if any(alias.name == "annotations" for alias in node.names):
                self._has_future_annotations = True
        elif node.module == "typing":
            names: list[ast.alias] = []
            for alias in node.names:
                if alias.name in IMPORTS_TO_REMOVE:
                    self._typing_imports[alias.asname or alias.name] = alias.name
                    self.add_token_func(
                        ast_to_offset(alias),
                        partial(remove_name_from_import, name=alias.name),
                    )
                else:
                    names.append(alias)
            if not names:
                self.add_token_func(ast_to_offset(node), remove_statement)
        else:
            return self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        """Transform typing.List -> list"""
        if (
            self.in_annotation
            and isinstance(node.value, ast.Name)
            and node.value.id == self.typing_import_name
            and node.attr in BASIC_COLLECTION_TYPES
        ):
            self.add_token_func(
                ast_to_offset(node),
                partial(replace_name, name=node.attr, new=node.attr.lower()),
            )
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> Any:
        if self.in_annotation and node.id in (
            set(self._typing_imports) & BASIC_COLLECTION_TYPES
        ):
            self.add_token_func(
                ast_to_offset(node),
                partial(
                    replace_name,
                    name=node.id,
                    new=self._typing_imports[node.id].lower(),
                ),
            )
        else:
            return self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        if isinstance(node.value, ast.Attribute):
            if (
                self.in_annotation
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == self.typing_import_name
            ):
                if node.value.attr == "Optional":
                    self.add_token_func(ast_to_offset(node), _fix_optional)
                elif node.value.attr == "Union":
                    arg_count = _get_arg_count(node.slice)
                    if arg_count > 0:
                        self.add_token_func(
                            ast_to_offset(node),
                            partial(_fix_union, arg_count=arg_count),
                        )
        elif isinstance(node.value, ast.Name):
            if self.in_annotation and node.value.id in self._typing_imports:
                if self._typing_imports[node.value.id] == "Optional":
                    self.add_token_func(ast_to_offset(node), _fix_optional)
                elif self._typing_imports[node.value.id] == "Union":
                    arg_count = _get_arg_count(node.slice)
                    if arg_count > 0:
                        self.add_token_func(
                            ast_to_offset(node),
                            partial(_fix_union, arg_count=arg_count),
                        )
        return self.generic_visit(node)
