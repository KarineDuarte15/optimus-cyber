"""Decorator de provider que repete chamadas após falhas temporárias."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from optimus_cyber.core.errors import ProviderTransientError
from optimus_cyber.core.interfaces.llm import LLMProvider, ProviderCapabilities
from optimus_cyber.core.models.llm import LLMRequest, LLMResponse
from optimus_cyber.observability.logging import get_logger, log_event

logger = get_logger("llm.retry")

Sleep = Callable[[float], Awaitable[None]]


class RetryingProvider(LLMProvider):
    """Envolve outro provider; só repete ``ProviderTransientError``.

    Backoff exponencial com jitter: ``base * 2**(tentativa-1)``, limitado a
    ``max_delay`` e multiplicado por um fator entre 0,5 e 1. Se o provider
    informar ``retry_after``, ele é respeitado (até ``max_delay``).
    """

    def __init__(
        self,
        inner: LLMProvider,
        *,
        max_retries: int,
        base_delay: float,
        max_delay: float = 30.0,
        sleep: Sleep = asyncio.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._inner = inner
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._sleep = sleep
        self._jitter = jitter

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def model(self) -> str:
        return self._inner.model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._inner.capabilities

    @property
    def inner(self) -> LLMProvider:
        """Provider envolvido."""
        return self._inner

    def delay_for(self, attempt: int, retry_after: float | None = None) -> float:
        """Espera antes da próxima tentativa (``attempt`` começa em 1)."""
        if retry_after is not None:
            return min(retry_after, self._max_delay)
        exponential = min(self._base_delay * float(2 ** (attempt - 1)), self._max_delay)
        return float(exponential * (0.5 + self._jitter() / 2))

    async def generate(self, request: LLMRequest) -> LLMResponse:
        attempt = 1
        while True:
            try:
                response = await self._inner.generate(request)
            except ProviderTransientError as exc:
                if attempt > self._max_retries:
                    raise
                delay = self.delay_for(attempt, exc.retry_after_seconds)
                log_event(
                    logger,
                    logging.WARNING,
                    "llm.retry",
                    provider=self.name,
                    attempt=attempt,
                    error=type(exc).__name__,
                    status_code=exc.status_code,
                    delay_seconds=round(delay, 2),
                )
                await self._sleep(delay)
                attempt += 1
            else:
                return response.model_copy(update={"attempts": attempt})
