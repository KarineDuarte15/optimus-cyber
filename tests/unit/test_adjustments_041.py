"""Ajustes da Etapa 04.1: mensagens de erro, modelo servido e logs com spinner."""

from __future__ import annotations

import asyncio
import io
import logging
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import anthropic
import httpx2
import pytest
from google.genai import errors as genai_errors
from pydantic import SecretStr
from rich.console import Console
from typer.testing import CliRunner

from fakes.providers import FakeProvider, make_response
from optimus_cyber.cli.app import app
from optimus_cyber.cli.router import CommandRouter
from optimus_cyber.cli.state import AppState
from optimus_cyber.cli.ui.presenter import Presenter
from optimus_cyber.cli.ui.theme import OPTIMUS_THEME
from optimus_cyber.config.settings import DEFAULT_MODELS, ProviderName
from optimus_cyber.core.errors import (
    ProviderRequestError,
    ProviderUnavailableError,
    _format_duration,
)
from optimus_cyber.core.models import FinishReason, LLMRequest, LLMResponse, Message
from optimus_cyber.llm.claude import ClaudeProvider
from optimus_cyber.llm.config import ProviderConfig
from optimus_cyber.llm.gemini import GeminiProvider
from optimus_cyber.llm.retry import RetryingProvider
from optimus_cyber.llm.service import LLMService
from optimus_cyber.observability.logging import (
    CurrentStderrHandler,
    configure_logging,
    get_logger,
    log_event,
)
from optimus_cyber.orchestration.orchestrator import DefaultOrchestrator
from optimus_cyber.security.redaction import SecretRedactor

REQUEST = LLMRequest(messages=(Message.user("oi"),))
runner = CliRunner()


def _config(model: str) -> ProviderConfig:
    return ProviderConfig(model=model, api_key=SecretStr("k" * 20), timeout_seconds=5)


# ------------------------------------------------------------ 1. modelo padrão
def test_default_gemini_model_is_available_to_new_keys() -> None:
    assert DEFAULT_MODELS[ProviderName.GEMINI] == "gemini-3.5-flash"


# ------------------------------------------------------------ 2. erro 404 e 5xx
def _gemini_failing(error: Exception, model: str = "gemini-9-pro") -> GeminiProvider:
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(side_effect=error)
    return GeminiProvider(_config(model), client=client)


def test_gemini_404_names_the_model() -> None:
    provider = _gemini_failing(genai_errors.ClientError(404, {"error": {"status": "NOT_FOUND"}}))
    with pytest.raises(ProviderRequestError) as exc:
        asyncio.run(provider.generate(REQUEST))
    assert "gemini-9-pro" in exc.value.message
    assert exc.value.hint is not None
    assert "OPTIMUS_MODEL" in exc.value.hint


def test_gemini_503_suggests_another_model() -> None:
    provider = _gemini_failing(genai_errors.ServerError(503, {"error": {"status": "UNAVAILABLE"}}))
    with pytest.raises(ProviderUnavailableError) as exc:
        asyncio.run(provider.generate(REQUEST))
    assert "gemini-9-pro" in exc.value.message
    assert exc.value.hint is not None
    assert "sobrecarregado" in exc.value.hint


@pytest.mark.parametrize(
    ("code", "expected", "hint_part"),
    [(404, ProviderRequestError, "OPTIMUS_MODEL"), (503, ProviderUnavailableError, "instantes")],
)
def test_claude_404_and_5xx(code: int, expected: type[Exception], hint_part: str) -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx2.Response(code, request=request, json={})
    error = anthropic.APIStatusError("erro", response=response, body=None)
    client = MagicMock()
    client.messages.create = AsyncMock(side_effect=error)
    provider = ClaudeProvider(_config("claude-x"), client=client)
    with pytest.raises(expected) as exc:
        asyncio.run(provider.generate(REQUEST))
    assert "claude-x" in str(exc.value)
    assert hint_part in (getattr(exc.value, "hint", None) or "")


# ------------------------------------------------------------ 3. tentativas
async def _no_sleep(_: float) -> None:
    return None


def test_final_error_reports_attempts_and_time() -> None:
    error = ProviderUnavailableError("Gemini indisponível.", provider="fake")
    retrying = RetryingProvider(FakeProvider([error]), max_retries=3, base_delay=0, sleep=_no_sleep)
    with pytest.raises(ProviderUnavailableError) as exc:
        asyncio.run(retrying.generate(REQUEST))
    assert exc.value.attempts == 4
    assert exc.value.elapsed_seconds is not None
    exc.value.elapsed_seconds = 75
    assert exc.value.display_message() == (
        "Gemini indisponível. Falhou após 4 tentativas em 1 min 15 s."
    )


def test_single_attempt_keeps_original_message() -> None:
    error = ProviderUnavailableError("fora do ar.", provider="fake")
    assert error.display_message() == "fora do ar."


@pytest.mark.parametrize(
    ("seconds", "text"), [(0.4, "0 s"), (12.6, "13 s"), (60, "1 min"), (125, "2 min 5 s")]
)
def test_format_duration(seconds: float, text: str) -> None:
    assert _format_duration(seconds) == text


def test_cli_shows_attempts() -> None:
    error = ProviderUnavailableError("Gemini indisponível.", provider="fake", hint="tente depois")
    retrying = RetryingProvider(FakeProvider([error]), max_retries=2, base_delay=0, sleep=_no_sleep)
    state = AppState(
        presenter=Presenter.create(no_color=True),
        router=CommandRouter(DefaultOrchestrator(lambda: LLMService(retrying))),
        workspace=Path.cwd(),
    )
    result = runner.invoke(app, ["ask", "pergunta"], obj=state)
    assert result.exit_code == 4
    assert "Falhou após 3 tentativas" in result.output
    assert "tente depois" in result.output


# ------------------------------------------------------------ 5. modelo servido
def _response(model: str, requested: str | None) -> LLMResponse:
    return LLMResponse(
        content="x",
        finish_reason=FinishReason.STOP,
        provider="gemini",
        model=model,
        requested_model=requested,
    )


@pytest.mark.parametrize(
    ("served", "requested", "redirected"),
    [
        ("gemini-3.6-flash", "gemini-3.5-flash", True),
        ("gemini-3.5-flash-001", "gemini-3.5-flash", False),
        ("gemini-3.5-flash", "gemini-3.5-flash", False),
        ("gemini-3.5-flash", None, False),
    ],
)
def test_model_redirect_detection(served: str, requested: str | None, redirected: bool) -> None:
    assert _response(served, requested).model_redirected is redirected


def test_presenter_shows_requested_and_served_model() -> None:
    out = Console(record=True, width=120, theme=OPTIMUS_THEME)
    presenter = Presenter(out, Console(record=True, theme=OPTIMUS_THEME))
    presenter.answer(_response("gemini-3.6-flash", "gemini-3.5-flash"))
    assert "gemini-3.5-flash → gemini-3.6-flash" in out.export_text()


def test_providers_fill_requested_model() -> None:
    fake = FakeProvider([make_response()])
    assert asyncio.run(fake.generate(REQUEST)).requested_model is None  # fakes não preenchem
    from google.genai import types

    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(
        return_value=types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(role="model", parts=[types.Part(text="ok")]),
                    finish_reason=types.FinishReason.STOP,
                )
            ],
            model_version="gemini-3.6-flash",
        )
    )
    response = asyncio.run(
        GeminiProvider(_config("gemini-3.5-flash"), client=client).generate(REQUEST)
    )
    assert (response.requested_model, response.model) == ("gemini-3.5-flash", "gemini-3.6-flash")


# ------------------------------------------------------------ 4. logs x spinner
def test_debug_logs_go_through_rich_while_spinner_runs() -> None:
    """Reproduz o defeito: com o spinner ativo, o log precisa passar pelo Rich."""
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=True, width=100)
    configure_logging(level="INFO", redactor=SecretRedactor(), debug=True)
    try:
        with console.status("Consultando o modelo..."):
            log_event(get_logger("teste"), logging.WARNING, "llm.retry", attempt=1)
            time.sleep(0.05)
    finally:
        configure_logging(level="INFO", redactor=SecretRedactor())
    assert "llm.retry" in buffer.getvalue()


def test_current_stderr_handler_follows_sys_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = CurrentStderrHandler()
    replacement = io.StringIO()
    monkeypatch.setattr(sys, "stderr", replacement)
    handler.emit(logging.LogRecord("x", logging.INFO, "", 0, "mensagem", None, None))
    assert "mensagem" in replacement.getvalue()
