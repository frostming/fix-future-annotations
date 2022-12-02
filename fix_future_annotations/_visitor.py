from __future__ import annotations

import ast
import contextlib
import sys
from functools import partial
from typing import Any, Callable, List, NamedTuple

from tokenize_rt import NON_CODING_TOKENS, Offset, Token

from fix_future_annotations._utils import (
    ast_to_offset,
    find_closing_bracket,
    find_token,
    remove_name_from_import,
    remove_statement,
    replace_name,
    replace_string,
)

BASIC_COLLECTION_TYPES = frozenset(
    {"Set", "List", "Tuple", "Dict", "FrozenSet", "Type"}
)
IMPORTS_TO_REMOVE = BASIC_COLLECTION_TYPES | frozenset({"Optional", "Union"})
TokenFunc = Callable[[int, List[Token]], None]


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


class State(NamedTuple):
    in_annotation: bool
    in_literal: bool


class AnnotationVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.token_funcs: dict[Offset, list[TokenFunc]] = {}

        self._typing_import_name: str | None = None
        self._typing_extensions_import_name: str | None = None
        self._has_future_annotations = False
        self._using_new_annotations = False
        self._state_stack: list[State] = []
        self._typing_imports_to_remove: dict[str, str] = {}
        self._literal_import_name: str | None = None
        self._conditional_callbacks: list[
            tuple[Callable[[], bool], Callable[[], None]]
        ] = []

    def add_token_func(self, offset: Offset, func: TokenFunc) -> None:
        self.token_funcs.setdefault(offset, []).append(func)

    def add_conditional_token_func(
        self, condition: Callable[[], bool], offset: Offset, func: TokenFunc
    ) -> None:
        self._conditional_callbacks.append(
            (condition, partial(self.add_token_func, offset, func))
        )

    def get_token_functions(self, tree: ast.Module) -> dict[Offset, list[TokenFunc]]:
        with self.under_state(State(False, False)):
            self.visit(tree)
        for condition, callback in self._conditional_callbacks:
            if condition():
                callback()
        return self.token_funcs

    @property
    def state(self) -> State:
        return self._state_stack[-1]

    @property
    def need_future_annotations(self) -> bool:
        return not self._has_future_annotations and (
            bool(self.token_funcs) or self._using_new_annotations
        )

    @contextlib.contextmanager
    def under_state(self, state: State) -> None:
        self._state_stack.append(state)
        try:
            yield
        finally:
            self._state_stack.pop()

    def generic_visit(self, node: ast.AST) -> Any:
        for field in reversed(node._fields):
            value = getattr(node, field)
            if field in {"annotation", "returns"}:
                ctx = self.under_state(self.state._replace(in_annotation=True))
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
                self._typing_import_name = alias.asname or alias.name
            elif alias.name == "typing_extensions":
                self._typing_extensions_import_name = alias.asname or alias.name
        return self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        if node.module == "__future__":
            if any(alias.name == "annotations" for alias in node.names):
                self._has_future_annotations = True
        elif node.module == "typing":
            names: set[str] = {(alias.asname or alias.name) for alias in node.names}
            for alias in reversed(node.names):
                key = alias.asname or alias.name
                if alias.name == "Literal":
                    self._literal_import_name = key
                if alias.name in IMPORTS_TO_REMOVE:
                    self._typing_imports_to_remove[key] = alias.name
                    self.add_conditional_token_func(
                        lambda key=key: key in self._typing_imports_to_remove,
                        ast_to_offset(alias if hasattr(alias, "lineno") else node),
                        partial(remove_name_from_import, name=alias.name),
                    )

            self.add_conditional_token_func(
                lambda names=names: names <= set(self._typing_imports_to_remove),
                ast_to_offset(node),
                remove_statement,
            )
        elif node.module == "typing_extensions":
            alias = next((a for a in node.names if a.name == "Literal"), None)
            if alias is not None:
                self._literal_import_name = alias.asname or alias.name
        else:
            return self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        """Transform typing.List -> list"""
        if (
            self.state.in_annotation
            and isinstance(node.value, ast.Name)
            and node.value.id == self._typing_import_name
            and node.attr in BASIC_COLLECTION_TYPES
        ):
            self.add_token_func(
                ast_to_offset(node),
                partial(replace_name, name=node.attr, new=node.attr.lower()),
            )
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self._typing_imports_to_remove:
            name = self._typing_imports_to_remove[node.id]
            if not self.state.in_annotation:
                # It is referred to outside of an annotation, so we need to exclude it
                self._conditional_callbacks.insert(
                    0,
                    (
                        lambda: True,
                        lambda key=node.id: self._typing_imports_to_remove.pop(
                            key, None
                        ),
                    ),
                )
            elif name in BASIC_COLLECTION_TYPES:
                self.add_token_func(
                    ast_to_offset(node),
                    partial(replace_name, name=node.id, new=name.lower()),
                )

        return self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if self.state.in_annotation:
            self._using_new_annotations = True
        return self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        if not self.state.in_annotation:
            return self.generic_visit(node)
        if isinstance(node.value, ast.Attribute):
            if (
                isinstance(node.value.value, ast.Name)
                and node.value.value.id == self._typing_import_name
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
            elif (
                isinstance(node.value.value, ast.Name)
                and node.value.value.id
                in {self._typing_import_name, self._typing_extensions_import_name}
                and node.value.attr == "Literal"
            ):
                with self.under_state(self.state._replace(in_literal=True)):
                    return self.generic_visit(node)
        elif isinstance(node.value, ast.Name):
            if node.value.id in self._typing_imports_to_remove:
                if self._typing_imports_to_remove[node.value.id] == "Optional":
                    self.add_token_func(ast_to_offset(node), _fix_optional)
                elif self._typing_imports_to_remove[node.value.id] == "Union":
                    arg_count = _get_arg_count(node.slice)
                    if arg_count > 0:
                        self.add_token_func(
                            ast_to_offset(node),
                            partial(_fix_union, arg_count=arg_count),
                        )
            elif node.value.id in {name.lower() for name in BASIC_COLLECTION_TYPES}:
                self._using_new_annotations = True
            elif node.value.id == self._literal_import_name:
                with self.under_state(self.state._replace(in_literal=True)):
                    return self.generic_visit(node)
        return self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if (
            self.state.in_annotation
            and not self.state.in_literal
            and isinstance(node.value, str)
        ):
            self.add_token_func(
                ast_to_offset(node), partial(replace_string, new=node.value)
            )
        return self.generic_visit(node)
