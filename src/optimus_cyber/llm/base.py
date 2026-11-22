"""Base dos adaptadores de SDK: timeout, latência, logs e tradução de erros."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import abstractmethod

from optimus_cyber.core.errors import (
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from optimus_cyber.core.interfaces.llm import LLMProvider
from optimus_cyber.core.models.llm import LLMRequest, LLMResponse
from optimus_cyber.llm.config import ProviderConfig
from optimus_cyber.observability.logging import get_logger, log_event

logger = get_logger("llm")

_NETWORK_MODULES = ("httpx", "httpx2", "httpcore", "aiohttp", "ssl", "socket")


def is_network_error(exc: BaseException) -> bool:
    """Falhas de rede vindas das bibliotecas HTTP usadas pelos SDKs."""
    module = type(exc).__module__.split(".")[0]
    return module in _NETWORK_MODULES or isinstance(exc, ConnectionError)


class SDKProvider(LLMProvider):
    """Implementa o fluxo comum; subclasses só traduzem formato e erros."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config

    @property
    def model(self) -> str:
        return self._config.model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        log_event(
            logger,
            logging.DEBUG,
            "llm.request",
            provider=self.name,
            model=self.model,
            messages=len(request.messages),
            input_chars=sum(len(m.content) for m in request.messages),
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )
        started = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                self._send(request), timeout=self._config.timeout_seconds
            )
        except TimeoutError as exc:
            raise ProviderTimeoutError(
                f"{self.name} não respondeu em {self._config.timeout_seconds:g} s.",
                provider=self.name,
                hint="Aumente OPTIMUS_REQUEST_TIMEOUT_SECONDS ou tente de novo.",
            ) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise self._translate_error(exc) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        log_event(
            logger,
            logging.INFO,
            "llm.response",
            provider=self.name,
            model=response.model,
            latency_ms=latency_ms,
            finish_reason=response.finish_reason.value,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            reasoning_tokens=response.usage.reasoning_tokens,
        )
        return response.model_copy(update={"latency_ms": latency_ms})

    @abstractmethod
    async def _send(self, request: LLMRequest) -> LLMResponse:
        """Chama o SDK e converte a resposta. Pode lançar exceções do SDK."""

    def _translate_error(self, exc: Exception) -> ProviderError:
        """Converte exceções do SDK. Subclasses tratam as próprias classes."""
        if is_network_error(exc):
            return ProviderUnavailableError(
                f"Falha de conexão com {self.name} ({type(exc).__name__}).",
                provider=self.name,
                hint="Verifique a internet, proxy ou firewall.",
            )
        return ProviderError(
            f"Erro inesperado no provider {self.name} ({type(exc).__name__}).",
            provider=self.name,
        )
