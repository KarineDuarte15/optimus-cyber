"""Garante que o pacote e todos os módulos da arquitetura importam."""

from __future__ import annotations

import ast
import importlib
import runpy
from pathlib import Path

import pytest

import optimus_cyber

MODULES = [
    "optimus_cyber.core",
    "optimus_cyber.core.interfaces",
    "optimus_cyber.core.models",
    "optimus_cyber.config",
    "optimus_cyber.config.settings",
    "optimus_cyber.cli",
    "optimus_cyber.cli.app",
    "optimus_cyber.cli.commands",
    "optimus_cyber.cli.ui",
    "optimus_cyber.orchestration",
    "optimus_cyber.agents",
    "optimus_cyber.tools",
    "optimus_cyber.llm",
    "optimus_cyber.security",
    "optimus_cyber.memory",
    "optimus_cyber.validation",
    "optimus_cyber.observability",
]


def test_version_is_defined() -> None:
    assert optimus_cyber.__version__
    assert isinstance(optimus_cyber.__version__, str)


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module: str) -> None:
    imported = importlib.import_module(module)
    assert imported.__doc__, f"{module} precisa de docstring descrevendo a responsabilidade"


def test_core_does_not_depend_on_other_modules() -> None:
    """Regra da arquitetura: core não importa nenhum outro módulo do pacote."""
    core_dir = Path(optimus_cyber.__file__).parent / "core"
    for source in core_dir.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                continue
            for name in names:
                if name.startswith("optimus_cyber."):
                    assert name.startswith("optimus_cyber.core"), f"{source}: importa {name}"


def test_python_m_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["optimus", "--version"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("optimus_cyber", run_name="__main__")
    assert exc.value.code == 0
