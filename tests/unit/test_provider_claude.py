"""ClaudeProvider com cliente mockado (sem rede)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx2
import pytest
from anthropic.types import Message as SDKMessage
from anthropic.types import TextBlock, Usage
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
from optimus_cyber.llm.claude import DEFAULT_MAX_TOKENS, ClaudeProvider, build_client
from optimus_cyber.llm.config import ProviderConfig

API_KEY = "sk-ant-api03-" + "z" * 30
CONFIG = ProviderConfig(model="claude-sonnet-5-5", api_key=SecretStr(API_KEY), timeout_seconds=5)
REQUEST = LLMRequest(
    messages=(Message.system("seja breve"), Message.user("explique X")),
    max_output_tokens=300,
)
_HTTP_REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def sdk_message(text: str = "resposta", stop: Any = "end_turn") -> SDKMessage:
    content: list[Any] = [TextBlock(type="text", text=text)] if text else []
    return SDKMessage(
        id="msg_1",
        type="message",
        role="assistant",
        model="claude-sonnet-5-5",
        content=content,
        stop_reason=stop,
        stop_sequence=None,
        usage=Usage(input_tokens=9, output_tokens=4),
    )


def status_error(cls: type[anthropic.APIStatusError], code: int, **headers: str) -> Exception:
    response = httpx2.Response(code, request=_HTTP_REQUEST, headers=headers, json={})
    return cls("erro", response=response, body=None)


def make_provider(
    result: Any = None, error: BaseException | None = None
) -> tuple[ClaudeProvider, AsyncMock]:
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=result, side_effect=error)
    return ClaudeProvider(CONFIG, client=client), client.messages.create


def test_translates_request_without_temperature() -> None:
    provider, call = make_provider(sdk_message())
    asyncio.run(provider.generate(REQUEST))
    assert call.await_args is not None
    kwargs = call.await_args.kwargs
    assert kwargs["model"] == "claude-sonnet-5-5"
    assert kwargs["system"] == "seja breve"
    assert kwargs["messages"] == [{"role": "user", "content": "explique X"}]
    assert kwargs["max_tokens"] == 300
    assert "temperature" not in kwargs


def test_uses_default_max_tokens_and_omits_empty_system() -> None:
    provider, call = make_provider(sdk_message())
    asyncio.run(provider.generate(LLMRequest(messages=(Message.user("oi"),))))
    assert call.await_args is not None
    kwargs = call.await_args.kwargs
    assert kwargs["max_tokens"] == DEFAULT_MAX_TOKENS
    assert "system" not in kwargs


def test_parses_response() -> None:
    provider, _ = make_provider(sdk_message("final"))
    response = asyncio.run(provider.generate(REQUEST))
    assert response.content == "final"
    assert response.finish_reason is FinishReason.STOP
    assert (response.usage.input_tokens, response.usage.output_tokens) == (9, 4)
    assert response.provider == "claude"


@pytest.mark.parametrize(
    ("stop", "expected"),
    [
        ("max_tokens", FinishReason.LENGTH),
        ("refusal", FinishReason.SAFETY),
        ("pause_turn", FinishReason.OTHER),
    ],
)
def test_stop_reasons(stop: str, expected: FinishReason) -> None:
    provider, _ = make_provider(sdk_message("x", stop=stop))
    assert asyncio.run(provider.generate(REQUEST)).finish_reason is expected


def test_empty_response() -> None:
    provider, _ = make_provider(sdk_message(""))
    with pytest.raises(ProviderResponseError):
        asyncio.run(provider.generate(REQUEST))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (status_error(anthropic.AuthenticationError, 401), ProviderAuthError),
        (status_error(anthropic.PermissionDeniedError, 403), ProviderAuthError),
        (status_error(anthropic.RateLimitError, 429), ProviderRateLimitError),
        (status_error(anthropic.BadRequestError, 400), ProviderRequestError),
        (status_error(anthropic.InternalServerError, 500), ProviderUnavailableError),
        (status_error(anthropic.APIStatusError, 529), ProviderUnavailableError),
        (anthropic.APITimeoutError(request=_HTTP_REQUEST), ProviderTimeoutError),
        (anthropic.APIConnectionError(request=_HTTP_REQUEST), ProviderUnavailableError),
        (RuntimeError("bug"), ProviderError),
    ],
)
def test_error_translation(error: Exception, expected: type[ProviderError]) -> None:
    provider, _ = make_provider(error=error)
    with pytest.raises(expected) as exc:
        asyncio.run(provider.generate(REQUEST))
    assert type(exc.value) is expected


def test_rate_limit_reads_retry_after() -> None:
    provider, _ = make_provider(
        error=status_error(anthropic.RateLimitError, 429, **{"retry-after": "7"})
    )
    with pytest.raises(ProviderRateLimitError) as exc:
        asyncio.run(provider.generate(REQUEST))
    assert exc.value.retry_after_seconds == 7


def test_invalid_retry_after_is_ignored() -> None:
    provider, _ = make_provider(
        error=status_error(anthropic.RateLimitError, 429, **{"retry-after": "tomorrow"})
    )
    with pytest.raises(ProviderRateLimitError) as exc:
        asyncio.run(provider.generate(REQUEST))
    assert exc.value.retry_after_seconds is None


def test_build_client_sets_timeout_and_disables_sdk_retry() -> None:
    with patch("optimus_cyber.llm.claude.anthropic.AsyncAnthropic") as client_cls:
        build_client(CONFIG)
    assert client_cls.call_args.kwargs == {
        "api_key": API_KEY,
        "timeout": 5,
        "max_retries": 0,
    }


def test_capabilities() -> None:
    provider, _ = make_provider(sdk_message())
    assert provider.name == "claude"
    assert not provider.capabilities.supports_temperature
