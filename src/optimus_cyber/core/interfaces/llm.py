"""Contrato único para qualquer modelo de linguagem.

Agentes e orquestrador dependem só desta interface. Um provider novo é uma
classe nova que a implementa, registrada na fábrica; nada mais muda.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from optimus_cyber.core.models.base import DomainModel
from optimus_cyber.core.models.llm import LLMRequest, LLMResponse


class ProviderCapabilities(DomainModel):
    """O que um provider aceita, para a camada de cima se adaptar."""

    supports_temperature: bool = True
    supports_system_prompt: bool = True
    max_output_tokens: int | None = None


class LLMProvider(ABC):
    """Gera respostas a partir de um ``LLMRequest``.

    Implementações devem traduzir erros do SDK para ``ProviderError`` e suas
    subclasses, e nunca expor tipos do SDK nem segredos.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador do provider (ex.: ``gemini``)."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Modelo usado nas chamadas."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Parâmetros suportados."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Gera uma resposta.

        Raises:
            ProviderAuthError: chave ausente ou inválida.
            ProviderRequestError: requisição rejeitada.
            ProviderResponseError: resposta vazia ou bloqueada.
            ProviderTransientError: falha temporária (pode ser repetida).
        """
