"""
python_parser.py

Extracts code entities (functions, classes, methods) and import
statements from Python source using the built-in `ast` module.

This module never executes the source it's given. It only parses it into
a syntax tree and walks that tree -- `ast.parse()` does not run any code.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from typing import Optional

from .entity_extractor import CodeEntity, EntityType, make_entity

logger = logging.getLogger(__name__)


@dataclass
class ImportInfo:
    """One import statement, kept separately from CodeEntity because
    imports aren't rows in `code_entities` -- they feed dependency_mapper's
    cross-file edges instead."""

    module: str          # e.g. "os.path" or "." for a relative import
    name: str            # the imported name, or "*" for `from x import *`
    alias: Optional[str]
    lineno: int


def _signature_for_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    try:
        args_src = ast.unparse(node.args)
    except Exception:
        # Extremely old ast edge cases -- fall back to just the names.
        args_src = ", ".join(a.arg for a in node.args.args)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({args_src})"


def _signature_for_class(node: ast.ClassDef, bases: list[str]) -> str:
    if bases:
        return f"class {node.name}({', '.join(bases)})"
    return f"class {node.name}"


def _collect_calls(node: ast.AST) -> list[str]:
    """Walk a function/method body and collect the names of everything it
    calls. Used later by dependency_mapper.py for same-file call edges --
    this module only extracts the raw names, it doesn't resolve them."""
    calls: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name):
                calls.add(func.id)
            elif isinstance(func, ast.Attribute):
                calls.add(func.attr)
    return sorted(calls)


class _EntityVisitor(ast.NodeVisitor):
    """Walks the module tree, tracking whether we're inside a class so
    nested functions are classified as methods vs. free functions."""

    def __init__(self, repository_id: Optional[str], file_id: Optional[str]):
        self.repository_id = repository_id
        self.file_id = file_id
        self.entities: list[CodeEntity] = []
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        entity = make_entity(
            entity_type=EntityType.CLASS,
            name=node.name,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            signature=_signature_for_class(node, bases),
            repository_id=self.repository_id,
            file_id=self.file_id,
            bases=bases,
        )
        self.entities.append(entity)

        self._class_stack.append(node.name)
        for child in node.body:
            self.visit(child)
        self._class_stack.pop()

    def _visit_function_like(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        in_class = bool(self._class_stack)
        entity_type = EntityType.METHOD if in_class else EntityType.FUNCTION
        name = f"{self._class_stack[-1]}.{node.name}" if in_class else node.name

        entity = make_entity(
            entity_type=entity_type,
            name=name,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            signature=_signature_for_function(node),
            repository_id=self.repository_id,
            file_id=self.file_id,
            calls=_collect_calls(node),
        )
        self.entities.append(entity)
        # Deliberately do not recurse into the function body here -- a
        # nested `def` inside a function is rare in practice for this
        # hackathon's scope, and recursing would double-count its calls
        # under both the outer and inner entity. Treat it as out of scope
        # rather than silently producing confusing duplicate entities.

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_like(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_like(node)


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: list[ImportInfo] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    name=alias.name,
                    alias=alias.asname,
                    lineno=node.lineno,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = ("." * (node.level or 0)) + (node.module or "")
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=module,
                    name=alias.name,
                    alias=alias.asname,
                    lineno=node.lineno,
                )
            )


def parse_python_file(
    source: str,
    file_id: Optional[str] = None,
    repository_id: Optional[str] = None,
) -> tuple[list[CodeEntity], list[ImportInfo]]:
    """
    Parse Python source into (entities, imports).

    Never raises on malformed input -- a syntax error is a normal outcome
    for arbitrary repository content (e.g. a file mid-refactor, or a file
    that isn't actually valid Python despite the extension). On a parse
    failure this returns ([], []) and logs a warning rather than crashing
    the whole analysis run for one bad file, consistent with the "graceful
    degradation" requirement in the PRD.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        logger.warning("python_parser: failed to parse file_id=%s: %s", file_id, exc)
        return [], []

    entity_visitor = _EntityVisitor(repository_id, file_id)
    entity_visitor.visit(tree)

    import_visitor = _ImportVisitor()
    import_visitor.visit(tree)

    return entity_visitor.entities, import_visitor.imports
