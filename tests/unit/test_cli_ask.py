"""optimus ask com LLM falso e com configuração real ausente."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fakes.providers import FakeProvider, make_response
from optimus_cyber.cli.app import app
from optimus_cyber.cli.router import CommandRouter
from optimus_cyber.cli.state import AppState
from optimus_cyber.cli.ui.presenter import Presenter
from optimus_cyber.core.errors import ProviderAuthError
from optimus_cyber.core.models import FinishReason
from optimus_cyber.llm.service import LLMService
from optimus_cyber.orchestration.orchestrator import DefaultOrchestrator

runner = CliRunner()


def _state(fake: FakeProvider) -> AppState:
    return AppState(
        presenter=Presenter.create(no_color=True),
        router=CommandRouter(DefaultOrchestrator(lambda: LLMService(fake))),
        workspace=Path.cwd(),
    )


def test_ask_renders_answer_and_usage() -> None:
    fake = FakeProvider([make_response("**SOLID** são cinco princípios.")])
    result = runner.invoke(app, ["ask", "o que é SOLID?"], obj=_state(fake))
    assert result.exit_code == 0, result.output
    assert "Resposta" in result.output
    assert "SOLID são cinco princípios." in result.output
    assert "10 → 5 tokens" in result.output
    assert "Em desenvolvimento" not in result.output


def test_ask_warns_when_truncated() -> None:
    fake = FakeProvider([make_response("parcial", finish=FinishReason.LENGTH)])
    result = runner.invoke(app, ["ask", "pergunta longa"], obj=_state(fake))
    assert result.exit_code == 0
    assert "cortada" in result.output


def test_ask_provider_error_exit_code() -> None:
    error = ProviderAuthError("chave recusada", provider="fake", hint="confira a chave")
    result = runner.invoke(app, ["ask", "pergunta"], obj=_state(FakeProvider([error])))
    assert result.exit_code == 4
    assert "chave recusada" in result.output
    assert "confira a chave" in result.output


def test_ask_without_key_explains_setup() -> None:
    result = runner.invoke(app, ["ask", "pergunta"])
    assert result.exit_code == 3
    assert "GEMINI_API_KEY" in result.output


def test_ask_with_claude_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIMUS_PROVIDER", "claude")
    result = runner.invoke(app, ["ask", "pergunta"])
    assert result.exit_code == 3
    assert "ANTHROPIC_API_KEY" in result.output
