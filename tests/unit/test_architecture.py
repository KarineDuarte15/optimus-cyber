"""Regras de arquitetura verificadas automaticamente."""

from __future__ import annotations

import ast
from pathlib import Path

import optimus_cyber

SRC = Path(optimus_cyber.__file__).parent
UI_DIR = SRC / "cli" / "ui"


def _calls(tree: ast.AST) -> list[ast.Call]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)]


def test_no_builtin_print_anywhere() -> None:
    for source in SRC.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for call in _calls(tree):
            is_print = isinstance(call.func, ast.Name) and call.func.id == "print"
            assert not is_print, f"print() em {source.relative_to(SRC)}:{call.lineno}"


def test_console_output_only_in_ui_layer() -> None:
    """Só cli/ui pode chamar .print()/.print_exception() de um Console."""
    for source in SRC.rglob("*.py"):
        if UI_DIR in source.parents:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for call in _calls(tree):
            func = call.func
            if isinstance(func, ast.Attribute) and func.attr in {"print", "print_exception"}:
                raise AssertionError(f"saída direta em {source.relative_to(SRC)}:{call.lineno}")
