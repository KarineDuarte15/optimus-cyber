"""Modelos neutros de conversa com LLM.

Nenhum tipo de SDK aparece aqui: cada adaptador traduz estes modelos para o
formato do seu provider e de volta.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from optimus_cyber.core.models.base import DomainModel

MAX_TEMPERATURE = 2.0


class Role(StrEnum):
    """Autor de uma mensagem."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(DomainModel):
    """Uma mensagem da conversa."""

    role: Role
    content: str = Field(min_length=1)

    @classmethod
    def system(cls, content: str) -> Message:
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> Message:
        return cls(role=Role.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        return cls(role=Role.ASSISTANT, content=content)


class LLMRequest(DomainModel):
    """Pedido de geração enviado a qualquer provider."""

    messages: tuple[Message, ...] = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0, le=MAX_TEMPERATURE)
    max_output_tokens: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _needs_conversation(self) -> LLMRequest:
        if not self.conversation:
            raise ValueError("é preciso ao menos uma mensagem de usuário ou assistente.")
        if self.conversation[-1].role is not Role.USER:
            raise ValueError("a última mensagem da conversa deve ser do usuário.")
        return self

    @property
    def system_prompt(self) -> str | None:
        """Instruções de sistema concatenadas (ou None)."""
        parts = [m.content for m in self.messages if m.role is Role.SYSTEM]
        return "\n\n".join(parts) if parts else None

    @property
    def conversation(self) -> tuple[Message, ...]:
        """Mensagens de usuário e assistente, na ordem."""
        return tuple(m for m in self.messages if m.role is not Role.SYSTEM)


class FinishReason(StrEnum):
    """Por que a geração terminou, normalizado entre providers."""

    STOP = "stop"
    LENGTH = "length"
    SAFETY = "safety"
    OTHER = "other"


class TokenUsage(DomainModel):
    """Contagem de tokens de uma chamada."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens + self.reasoning_tokens


class LLMResponse(DomainModel):
    """Resposta estruturada devolvida por qualquer provider."""

    content: str
    finish_reason: FinishReason
    usage: TokenUsage = TokenUsage()
    provider: str
    model: str
    requested_model: str | None = None
    latency_ms: int = Field(default=0, ge=0)
    attempts: int = Field(default=1, ge=1)

    @property
    def model_redirected(self) -> bool:
        """True quando a API serviu um modelo diferente do pedido.

        Sufixos de versão (``gemini-x`` → ``gemini-x-001``) não contam.
        """
        if not self.requested_model:
            return False
        return not self.model.startswith(self.requested_model)

    @property
    def truncated(self) -> bool:
        """True quando a resposta foi cortada pelo limite de tokens."""
        return self.finish_reason is FinishReason.LENGTH
