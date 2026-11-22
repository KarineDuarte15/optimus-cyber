"""Hierarquia de exceções do Optimus Cyber.

Falhas de infraestrutura e de uso sobem como exceções tipadas; a CLI as
converte em mensagem amigável e exit code. Mensagens nunca incluem segredos.
"""

from __future__ import annotations

from typing import ClassVar


class OptimusError(Exception):
    """Base de todas as exceções do Optimus Cyber."""

    exit_code: ClassVar[int] = 1

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class InputError(OptimusError):
    """Entrada do usuário inválida após o parsing dos argumentos."""

    exit_code: ClassVar[int] = 2


class ConfigError(OptimusError):
    """Configuração ausente ou inválida."""

    exit_code: ClassVar[int] = 3


# --------------------------------------------------------------- providers
class ProviderError(OptimusError):
    """Falha ao falar com um provedor de LLM."""

    exit_code: ClassVar[int] = 4
    retryable: ClassVar[bool] = False

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        status_code: int | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message, hint=hint)
        self.provider = provider
        self.status_code = status_code


class ProviderAuthError(ProviderError):
    """Chave ausente, inválida ou sem permissão. Não adianta repetir."""


class ProviderRequestError(ProviderError):
    """Requisição rejeitada (modelo inexistente, parâmetro inválido)."""


class ProviderResponseError(ProviderError):
    """Resposta vazia, bloqueada por segurança ou malformada."""


class ProviderTransientError(ProviderError):
    """Falha temporária: vale tentar de novo."""

    retryable: ClassVar[bool] = True

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        status_code: int | None = None,
        hint: str | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message, provider=provider, status_code=status_code, hint=hint)
        self.retry_after_seconds = retry_after_seconds


class ProviderRateLimitError(ProviderTransientError):
    """Limite de requisições ou de cota atingido (HTTP 429)."""


class ProviderTimeoutError(ProviderTransientError):
    """A chamada excedeu o timeout configurado."""


class ProviderUnavailableError(ProviderTransientError):
    """Erro de servidor (5xx), sobrecarga ou falha de conexão."""
