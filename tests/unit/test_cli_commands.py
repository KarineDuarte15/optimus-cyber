"""Testes de ponta a ponta da CLI com o orquestrador stub."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from optimus_cyber import __version__
from optimus_cyber.cli.app import app
from optimus_cyber.cli.ui.labels import APP_TITLE

runner = CliRunner()

COMMANDS = [
    "ask",
    "doctor",
    "explain",
    "fix",
    "review",
    "test",
    "commit",
    "docs",
    "project",
    "status",
]


def test_root_help_lists_every_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in COMMANDS:
        assert command in result.output


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "doctor" in result.output


@pytest.mark.parametrize("command", COMMANDS)
def test_every_command_has_help(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


@pytest.mark.parametrize("flag", ["--version", "-V"])
def test_version(flag: str) -> None:
    result = runner.invoke(app, [flag])
    assert result.exit_code == 0
    assert __version__ in result.output


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    path = tmp_path / "app.log"
    path.write_text("Traceback (most recent call last):\nKeyError: 'id'\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("args", "mode"),
    [
        (["ask", "onde fica a autenticação?"], "Modo Pergunta"),
        (["doctor"], "Modo Diagnóstico"),
        (["doctor", "--cmd", "pytest"], "Modo Diagnóstico"),
        (["explain", "KeyError: 'id'"], "Modo Explicação"),
        (["fix", "--issue", "login quebrado", "--dry-run"], "Modo Correção"),
        (["review", "--focus", "security"], "Modo Revisão"),
        (["review", "--staged"], "Modo Revisão"),
        (["test", "-k", "login", "--coverage", "-x"], "Modo Testes"),
        (["commit", "--type", "feat", "--scope", "cli"], "Modo Commit"),
        (["docs", "--target", "changelog"], "Modo Documentação"),
        (["project", "--depth", "3"], "Modo Projeto"),
    ],
)
def test_commands_render_plan(args: list[str], mode: str) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert APP_TITLE in result.output
    assert mode in result.output
    assert "Plano de execução" in result.output
    assert "Em desenvolvimento" in result.output


def test_commands_accept_log_file(log_file: Path) -> None:
    for args in (["doctor", "--log"], ["explain", "--log"], ["fix", "--log"]):
        result = runner.invoke(app, [*args, str(log_file)])
        assert result.exit_code == 0, result.output


def test_review_accepts_existing_paths(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    target.write_text("x = 1\n", encoding="utf-8")
    result = runner.invoke(app, ["review", str(target)])
    assert result.exit_code == 0, result.output


def test_enum_options_are_case_insensitive() -> None:
    result = runner.invoke(app, ["docs", "--target", "README"])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    "args",
    [
        ["ask"],
        ["ask", "   "],
        ["ask", "ab"],
        ["doctor", "--log", "nao-existe.log"],
        ["doctor", "--cmd", "   "],
        ["explain"],
        ["fix"],
        ["fix", "--issue", ""],
        ["review", "--focus", "beleza"],
        ["review", "nao-existe.py"],
        ["test", "-k", "  "],
        ["commit", "--type", "wip"],
        ["commit", "--scope", "Escopo Inválido"],
        ["docs", "--target", "wiki"],
        ["project", "--depth", "0"],
        ["project", "--depth", "7"],
        ["project", "--depth", "dois"],
        ["--path", "pasta-que-nao-existe", "doctor"],
        ["comando-inexistente"],
    ],
)
def test_invalid_input_exits_with_usage_error(args: list[str]) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 2, result.output


def test_doctor_rejects_log_and_cmd_together(log_file: Path) -> None:
    result = runner.invoke(app, ["doctor", "--log", str(log_file), "--cmd", "pytest"])
    assert result.exit_code == 2
    assert "use apenas um de" in result.output


def test_explain_rejects_text_and_log_together(log_file: Path) -> None:
    result = runner.invoke(app, ["explain", "erro", "--log", str(log_file)])
    assert result.exit_code == 2


def test_review_rejects_paths_with_staged(tmp_path: Path) -> None:
    result = runner.invoke(app, ["review", str(tmp_path), "--staged"])
    assert result.exit_code == 2


def test_fix_requires_issue_or_log() -> None:
    result = runner.invoke(app, ["fix"])
    assert "informe ao menos um de" in result.output
