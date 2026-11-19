"""Configuração da aplicação lida de variáveis de ambiente e do arquivo .env.

Segredos (chaves de API) entram somente por ambiente e são tipados como
``SecretStr`` para não aparecerem em ``repr``, logs ou mensagens de erro.
A leitura do ``optimus.toml`` será adicionada na Etapa 04.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderName(StrEnum):
    """Provedores de LLM suportados."""

    GEMINI = "gemini"
    CLAUDE = "claude"


class LogLevel(StrEnum):
    """Níveis de log aceitos."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class AppSettings(BaseSettings):
    """Configuração global do Optimus Cyber.

    Variáveis com prefixo ``OPTIMUS_`` controlam o comportamento; as chaves
    de API usam os nomes padrão de cada provedor.
    """

    model_config = SettingsConfigDict(
        env_prefix="OPTIMUS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    primary_provider: ProviderName = ProviderName.GEMINI
    secondary_provider: ProviderName | None = ProviderName.CLAUDE
    primary_model: str = "gemini-2.5-pro"
    secondary_model: str | None = None
    log_level: LogLevel = LogLevel.INFO
    request_timeout_seconds: float = Field(default=120.0, gt=0)

    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    def has_key_for(self, provider: ProviderName) -> bool:
        """Indica se há chave configurada para o provedor, sem expô-la."""
        key = self.gemini_api_key if provider is ProviderName.GEMINI else self.anthropic_api_key
        return key is not None and bool(key.get_secret_value())


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Retorna a configuração carregada uma única vez por processo."""
    return AppSettings()
