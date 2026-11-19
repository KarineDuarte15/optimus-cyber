"""Tratamento de erros: mensagem amigável, exit code certo, sem traceback cru."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from fakes.runners import FailingRunner
from optimus_cyber.cli.app import app
from optimus_cyber.cli.errors import EXIT_INTERRUPTED, EXIT_UNEXPECTED, handle_errors
from optimus_cyber.cli.router import CommandRouter
from optimus_cyber.cli.state import AppState, get_state
from optimus_cyber.cli.ui.presenter import Presenter
from optimus_cyber.core.errors import ConfigError, InputError

runner = CliRunner()


def _state(error: BaseException) -> AppState:
    return AppState(
        presenter=Presenter.create(no_color=True),
        router=CommandRouter(FailingRunner(error)),
        workspace=Path.cwd(),
    )


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ConfigError("sem chave", hint="defina GEMINI_API_KEY"), 3),
        (InputError("entrada ruim"), 2),
    ],
)
def test_optimus_errors_map_to_exit_codes(error: ConfigError | InputError, code: int) -> None:
    result = runner.invoke(app, ["doctor"], obj=_state(error))
    assert result.exit_code == code
    assert error.message in result.output
    if error.hint:
        assert error.hint in result.output


def test_unexpected_error_hides_traceback() -> None:
    result = runner.invoke(app, ["doctor"], obj=_state(ValueError("detalhe interno")))
    assert result.exit_code == EXIT_UNEXPECTED
    assert "Erro inesperado: ValueError" in result.output
    assert "Traceback" not in result.output
    assert "--debug" in result.output


def test_debug_shows_traceback() -> None:
    result = runner.invoke(app, ["--debug", "doctor"], obj=_state(ValueError("detalhe")))
    assert result.exit_code == EXIT_UNEXPECTED
    assert "Traceback" in result.output


def test_keyboard_interrupt_exits_130() -> None:
    result = runner.invoke(app, ["doctor"], obj=_state(KeyboardInterrupt()))
    assert result.exit_code == EXIT_INTERRUPTED
    assert "cancelada" in result.output


def test_handle_errors_without_context(capsys: pytest.CaptureFixture[str]) -> None:
    """Sem ctx, o decorator ainda usa um Presenter padrão."""

    @handle_errors
    def broken() -> None:
        raise InputError("sem contexto")

    with pytest.raises(typer.Exit) as exc:
        broken()
    assert exc.value.exit_code == 2
    assert "sem contexto" in capsys.readouterr().err


def test_get_state_requires_initialization() -> None:
    with pytest.raises(RuntimeError):
        get_state(typer.Context(typer.main.get_command(app)))
