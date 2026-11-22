"""API de alto nível: ``generate()``.

É o ponto de entrada que agentes e orquestrador usam. Aplica os padrões da
configuração, adapta o pedido às capacidades do provider e devolve um
``LLMResponse`` estruturado.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from optimus_cyber.config.settings import AppSettings, ProviderName, get_settings
from optimus_cyber.core.interfaces.llm import LLMProvider
from optimus_cyber.core.models.llm import LLMRequest, LLMResponse, Message
from optimus_cyber.llm.factory import create_provider
from optimus_cyber.observability.logging import get_logger, log_event

logger = get_logger("llm.service")

Prompt = str | Message | Sequence[Message]


def _to_messages(prompt: Prompt, system: str | None) -> tuple[Message, ...]:
    if isinstance(prompt, str):
        messages: list[Message] = [Message.user(prompt)]
    elif isinstance(prompt, Message):
        messages = [prompt]
    else:
        messages = list(prompt)
    if system:
        messages.insert(0, Message.system(system))
    return tuple(messages)


class LLMService:
    """Fachada sobre um ``LLMProvider`` com padrões de geração."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        self._provider = provider
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

    @classmethod
    def from_settings(
        cls, settings: AppSettings | None = None, provider: ProviderName | None = None
    ) -> LLMService:
        """Monta o serviço a partir da configuração (ambiente e .env)."""
        settings = settings or get_settings()
        return cls(
            create_provider(settings, provider),
            temperature=settings.temperature,
            max_output_tokens=settings.max_output_tokens,
        )

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    async def generate(
        self,
        prompt: Prompt,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        """Gera uma resposta.

        Args:
            prompt: texto do usuário, uma ``Message`` ou a conversa inteira.
            system: instruções de sistema (somadas às da conversa, se houver).
            temperature: sobrescreve o padrão; ignorada se o provider não aceita.
            max_output_tokens: sobrescreve o limite padrão.
        """
        chosen_temperature = temperature if temperature is not None else self._temperature
        if chosen_temperature is not None and not self._provider.capabilities.supports_temperature:
            log_event(
                logger,
                logging.DEBUG,
                "llm.param_ignored",
                provider=self._provider.name,
                param="temperature",
            )
            chosen_temperature = None

        request = LLMRequest(
            messages=_to_messages(prompt, system),
            temperature=chosen_temperature,
            max_output_tokens=max_output_tokens or self._max_output_tokens,
        )
        return await self._provider.generate(request)


async def generate(
    prompt: Prompt,
    *,
    system: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    provider: ProviderName | None = None,
    settings: AppSettings | None = None,
) -> LLMResponse:
    """Atalho: cria o serviço pela configuração e gera uma resposta.

    Exemplo::

        response = await generate("Explique este erro: KeyError 'id'")
        print(response.content, response.usage.total)
    """
    service = LLMService.from_settings(settings, provider)
    return await service.generate(
        prompt, system=system, temperature=temperature, max_output_tokens=max_output_tokens
    )
