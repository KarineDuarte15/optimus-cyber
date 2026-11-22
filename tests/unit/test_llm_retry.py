"""RetryingProvider."""

from __future__ import annotations

import asyncio

import pytest

from fakes.providers import FakeProvider, make_response
from optimus_cyber.core.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from optimus_cyber.core.models import LLMRequest, Message
from optimus_cyber.llm.retry import RetryingProvider

REQUEST = LLMRequest(messages=(Message.user("oi"),))


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def _transient(retry_after: float | None = None) -> ProviderUnavailableError:
    return ProviderUnavailableError("fora", provider="fake", retry_after_seconds=retry_after)


def _retrying(fake: FakeProvider, sleep: SleepRecorder, retries: int = 3) -> RetryingProvider:
    return RetryingProvider(
        fake, max_retries=retries, base_delay=1.0, max_delay=30, sleep=sleep, jitter=lambda: 1.0
    )


def test_retries_transient_errors_with_exponential_backoff() -> None:
    sleep = SleepRecorder()
    fake = FakeProvider(
        [
            _transient(),
            ProviderTimeoutError("lento", provider="fake"),
            ProviderRateLimitError("cota", provider="fake"),
            make_response("ok"),
        ]
    )
    response = asyncio.run(_retrying(fake, sleep).generate(REQUEST))
    assert response.content == "ok"
    assert response.attempts == 4
    assert sleep.delays == [1.0, 2.0, 4.0]


def test_gives_up_after_max_retries() -> None:
    sleep = SleepRecorder()
    fake = FakeProvider([_transient()])
    with pytest.raises(ProviderUnavailableError):
        asyncio.run(_retrying(fake, sleep, retries=2).generate(REQUEST))
    assert len(fake.requests) == 3
    assert len(sleep.delays) == 2


def test_does_not_retry_permanent_errors() -> None:
    sleep = SleepRecorder()
    fake = FakeProvider([ProviderAuthError("chave", provider="fake")])
    with pytest.raises(ProviderAuthError):
        asyncio.run(_retrying(fake, sleep).generate(REQUEST))
    assert len(fake.requests) == 1
    assert sleep.delays == []


def test_zero_retries_means_single_attempt() -> None:
    fake = FakeProvider([_transient()])
    with pytest.raises(ProviderUnavailableError):
        asyncio.run(_retrying(fake, SleepRecorder(), retries=0).generate(REQUEST))
    assert len(fake.requests) == 1


def test_retry_after_is_respected_and_capped() -> None:
    sleep = SleepRecorder()
    fake = FakeProvider([_transient(retry_after=5), _transient(retry_after=999), make_response()])
    asyncio.run(_retrying(fake, sleep).generate(REQUEST))
    assert sleep.delays == [5, 30]


def test_delay_is_capped_and_jittered() -> None:
    provider = RetryingProvider(
        FakeProvider(), max_retries=10, base_delay=1, max_delay=8, jitter=lambda: 0.0
    )
    assert provider.delay_for(1) == 0.5
    assert provider.delay_for(10) == 4.0


def test_exposes_inner_identity() -> None:
    fake = FakeProvider(supports_temperature=False)
    provider = _retrying(fake, SleepRecorder())
    assert (provider.name, provider.model, provider.inner) == ("fake", "fake-model", fake)
    assert not provider.capabilities.supports_temperature
