"""Garante que a CLI monta a requisição certa para a orquestração."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from fakes.runners import RecordingRunner
from optimus_cyber.cli.app import app
from optimus_cyber.cli.router import CommandRouter
from optimus_cyber.cli.state import AppState
from optimus_cyber.cli.ui.presenter import Presenter
from optimus_cyber.core.models import Intent, UserRequest

runner = CliRunner()


def _invoke(args: list[str], fake: RecordingRunner) -> UserRequest:
    state = AppState(
        presenter=Presenter.create(no_color=True),
        router=CommandRouter(fake),
        workspace=Path.cwd(),
    )
    result = runner.invoke(app, args, obj=state)
    assert result.exit_code == 0, result.output
    assert len(fake.requests) == 1
    return fake.requests[0]


def test_ask_sends_trimmed_question() -> None:
    request = _invoke(["ask", "  como roda?  "], RecordingRunner())
    assert request.intent is Intent.ASK
    assert request.text == "como roda?"


def test_fix_sends_flags() -> None:
    request = _invoke(["fix", "-i", "erro 500", "--yes"], RecordingRunner())
    assert request.intent is Intent.FIX
    assert request.text == "erro 500"
    assert request.options == {"dry_run": False, "auto_approve": True}


def test_unset_options_are_dropped() -> None:
    request = _invoke(["commit"], RecordingRunner())
    assert request.options == {}


def test_review_paths_become_tuple(tmp_path: Path) -> None:
    first = tmp_path / "a.py"
    first.write_text("", encoding="utf-8")
    request = _invoke(["review", str(first)], RecordingRunner())
    assert request.options["paths"] == (str(first),)
    assert request.options["focus"] == "all"


def test_global_path_sets_workspace(tmp_path: Path) -> None:
    request = _invoke(["--path", str(tmp_path), "project"], RecordingRunner())
    assert request.workspace == tmp_path.resolve()
    assert request.intent is Intent.PROJECT


def test_completed_outcome_is_rendered() -> None:
    fake = RecordingRunner()
    state = AppState(
        presenter=Presenter.create(no_color=True),
        router=CommandRouter(fake),
        workspace=Path.cwd(),
    )
    result = runner.invoke(app, ["docs"], obj=state)
    assert "Concluído" in result.output
    assert "Em desenvolvimento" not in result.output
