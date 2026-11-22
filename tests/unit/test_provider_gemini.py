"""GeminiProvider com cliente mockado (sem rede)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx2
import pytest
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import SecretStr

from optimus_cyber.core.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from optimus_cyber.core.models import FinishReason, LLMRequest, Message
from optimus_cyber.llm.config import ProviderConfig
from optimus_cyber.llm.gemini import GeminiProvider, build_client
from optimus_cyber.observability.logging import configure_logging
from optimus_cyber.security.redaction import SecretRedactor

API_KEY = "AIza" + "K" * 35
CONFIG = ProviderConfig(model="gemini-2.5-pro", api_key=SecretStr(API_KEY), timeout_seconds=5)
REQUEST = LLMRequest(
    messages=(
        Message.system("seja breve"),
        Message.user("oi"),
        Message.assistant("olá"),
        Message.user("explique X"),
    ),
    temperature=0.3,
    max_output_tokens=500,
)


def gemini_response(
    text: str | None = "resposta",
    *,
    finish: types.FinishReason = types.FinishReason.STOP,
    thought: str | None = None,
    blocked: bool = False,
    candidates: bool = True,
) -> types.GenerateContentResponse:
    parts = []
    if thought:
        parts.append(types.Part(text=thought, thought=True))
    if text:
        parts.append(types.Part(text=text))
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(content=types.Content(role="model", parts=parts), finish_reason=finish)
        ]
        if candidates
        else [],
        prompt_feedback=types.GenerateContentResponsePromptFeedback(
            block_reason=types.BlockedReason.SAFETY
        )
        if blocked
        else None,
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=12, candidates_token_count=7, thoughts_token_count=30
        ),
        model_version="gemini-2.5-pro-001",
    )


def make_provider(
    result: Any = None, error: BaseException | None = None
) -> tuple[GeminiProvider, AsyncMock]:
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=result, side_effect=error)
    return GeminiProvider(CONFIG, client=client), client.aio.models.generate_content


def test_translates_request_to_sdk_format() -> None:
    provider, call = make_provider(gemini_response())
    asyncio.run(provider.generate(REQUEST))
    assert call.await_args is not None
    kwargs = call.await_args.kwargs
    assert kwargs["model"] == "gemini-2.5-pro"
    assert [c.role for c in kwargs["contents"]] == ["user", "model", "user"]
    assert kwargs["contents"][-1].parts[0].text == "explique X"
    config = kwargs["config"]
    assert config.system_instruction == "seja breve"
    assert config.temperature == 0.3
    assert config.max_output_tokens == 500


def test_parses_structured_response_and_skips_thoughts() -> None:
    provider, _ = make_provider(gemini_response("final", thought="pensando..."))
    response = asyncio.run(provider.generate(REQUEST))
    assert response.content == "final"
    assert response.finish_reason is FinishReason.STOP
    assert response.provider == "gemini"
    assert response.model == "gemini-2.5-pro-001"
    assert (response.usage.input_tokens, response.usage.output_tokens) == (12, 7)
    assert response.usage.reasoning_tokens == 30
    assert response.latency_ms >= 0


@pytest.mark.parametrize(
    ("sdk_reason", "expected"),
    [
        (types.FinishReason.MAX_TOKENS, FinishReason.LENGTH),
        (types.FinishReason.SAFETY, FinishReason.SAFETY),
        (types.FinishReason.OTHER, FinishReason.OTHER),
    ],
)
def test_finish_reasons(sdk_reason: types.FinishReason, expected: FinishReason) -> None:
    provider, _ = make_provider(gemini_response("parcial", finish=sdk_reason))
    assert asyncio.run(provider.generate(REQUEST)).finish_reason is expected


def test_empty_text_after_max_tokens_explains_thinking_budget() -> None:
    provider, _ = make_provider(
        gemini_response(None, finish=types.FinishReason.MAX_TOKENS, thought="só pensou")
    )
    with pytest.raises(ProviderResponseError) as exc:
        asyncio.run(provider.generate(REQUEST))
    assert exc.value.hint is not None
    assert "OPTIMUS_MAX_OUTPUT_TOKENS" in exc.value.hint


@pytest.mark.parametrize("raw", [gemini_response(blocked=True), gemini_response(candidates=False)])
def test_blocked_or_missing_candidates(raw: types.GenerateContentResponse) -> None:
    provider, _ = make_provider(raw)
    with pytest.raises(ProviderResponseError):
        asyncio.run(provider.generate(REQUEST))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            genai_errors.ClientError(401, {"error": {"message": "bad", "status": "UNAUTH"}}),
            ProviderAuthError,
        ),
        (genai_errors.ClientError(403, {"error": {"message": "denied"}}), ProviderAuthError),
        (genai_errors.ClientError(429, {"error": {"message": "quota"}}), ProviderRateLimitError),
        (genai_errors.ClientError(404, {"error": {"message": "model"}}), ProviderRequestError),
        (genai_errors.ServerError(503, {"error": {"message": "busy"}}), ProviderUnavailableError),
        (httpx2.ConnectError("sem rede"), ProviderUnavailableError),
        (RuntimeError("bug"), ProviderError),
    ],
)
def test_error_translation(error: Exception, expected: type[ProviderError]) -> None:
    provider, _ = make_provider(error=error)
    with pytest.raises(expected) as exc:
        asyncio.run(provider.generate(REQUEST))
    assert type(exc.value) is expected
    assert exc.value.provider == "gemini"


def test_error_message_never_contains_api_key() -> None:
    error = genai_errors.ClientError(400, {"error": {"message": f"chave {API_KEY} inválida"}})
    provider, _ = make_provider(error=error)
    with pytest.raises(ProviderRequestError) as exc:
        asyncio.run(provider.generate(REQUEST))
    assert API_KEY not in str(exc.value)
    assert API_KEY not in (exc.value.hint or "")


def test_timeout() -> None:
    async def slow(**_: Any) -> None:
        await asyncio.sleep(1)

    client = MagicMock()
    client.aio.models.generate_content = slow
    config = CONFIG.model_copy(update={"timeout_seconds": 0.01})
    with pytest.raises(ProviderTimeoutError):
        asyncio.run(GeminiProvider(config, client=client).generate(REQUEST))


def test_build_client_sets_timeout_and_disables_sdk_retry() -> None:
    with patch("optimus_cyber.llm.gemini.genai.Client") as client_cls:
        build_client(CONFIG)
    kwargs = client_cls.call_args.kwargs
    assert kwargs["api_key"] == API_KEY
    assert kwargs["http_options"].timeout == 5000
    assert kwargs["http_options"].retry_options.attempts == 1


def test_capabilities_and_identity() -> None:
    provider, _ = make_provider(gemini_response())
    assert provider.name == "gemini"
    assert provider.model == "gemini-2.5-pro"
    assert provider.capabilities.supports_temperature


def test_logs_never_contain_prompt_or_key(tmp_path: Path) -> None:
    log_file = tmp_path / "llm.log"
    configure_logging(level="DEBUG", redactor=SecretRedactor([API_KEY]), log_file=log_file)
    provider, _ = make_provider(gemini_response("conteúdo da resposta"))
    asyncio.run(provider.generate(REQUEST))
    configure_logging(level="INFO", redactor=SecretRedactor())
    text = log_file.read_text(encoding="utf-8")
    assert "llm.request" in text
    assert "llm.response" in text
    assert "explique X" not in text
    assert "conteúdo da resposta" not in text
    assert API_KEY not in text
