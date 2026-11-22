"""Configuração da aplicação lida de variáveis de ambiente e do arquivo .env.

Segredos (chaves de API) entram somente por ambiente e são tipados como
``SecretStr`` para não aparecerem em ``repr``, logs ou mensagens de erro.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from optimus_cyber.core.errors import ConfigError


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


DEFAULT_MODELS: dict[ProviderName, str] = {
    ProviderName.GEMINI: "gemini-3.5-flash",
    ProviderName.CLAUDE: "claude-sonnet-5-5",
}

API_KEY_ENV: dict[ProviderName, str] = {
    ProviderName.GEMINI: "GEMINI_API_KEY",
    ProviderName.CLAUDE: "ANTHROPIC_API_KEY",
}


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

    # --- providers -------------------------------------------------------
    primary_provider: ProviderName = Field(
        default=ProviderName.GEMINI,
        validation_alias=AliasChoices("OPTIMUS_PROVIDER", "OPTIMUS_PRIMARY_PROVIDER"),
    )
    primary_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPTIMUS_MODEL", "OPTIMUS_PRIMARY_MODEL"),
    )
    secondary_provider: ProviderName | None = ProviderName.CLAUDE
    secondary_model: str | None = None

    # --- geração -----------------------------------------------------------
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_output_tokens: int = Field(default=8192, gt=0, le=65536)

    # --- resiliência -------------------------------------------------------
    request_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_base_delay_seconds: float = Field(default=1.0, ge=0, le=60)

    # --- logs --------------------------------------------------------------
    log_level: LogLevel = LogLevel.INFO
    log_file: Path | None = None

    # --- segredos ----------------------------------------------------------
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    def api_key_for(self, provider: ProviderName) -> SecretStr | None:
        """Chave do provider, ou None se ausente ou vazia."""
        key = self.gemini_api_key if provider is ProviderName.GEMINI else self.anthropic_api_key
        if key is None or not key.get_secret_value().strip():
            return None
        return key

    def has_key_for(self, provider: ProviderName) -> bool:
        """Indica se há chave configurada para o provider, sem expô-la."""
        return self.api_key_for(provider) is not None

    def model_for(self, provider: ProviderName) -> str:
        """Modelo configurado para o provider, ou o padrão dele."""
        if provider is self.primary_provider and self.primary_model:
            return self.primary_model
        if provider is self.secondary_provider and self.secondary_model:
            return self.secondary_model
        return DEFAULT_MODELS[provider]

    def secret_values(self) -> list[str]:
        """Valores secretos configurados, para o redator de logs."""
        keys = (self.gemini_api_key, self.anthropic_api_key)
        return [key.get_secret_value() for key in keys if key and key.get_secret_value()]


def _env_name(location: str) -> str:
    """Nome da variável de ambiente correspondente a um campo."""
    return location if location.isupper() else f"OPTIMUS_{location.upper()}"


def load_settings() -> AppSettings:
    """Carrega a configuração, convertendo erros de validação em ``ConfigError``.

    A mensagem cita só o nome das variáveis, nunca os valores (podem ser segredos).
    """
    try:
        return AppSettings()
    except ValidationError as exc:
        fields = sorted({_env_name(str(err["loc"][0])) for err in exc.errors() if err["loc"]})
        raise ConfigError(
            f"Configuração inválida: {', '.join(fields)}.",
            hint="Confira o .env ou as variáveis OPTIMUS_* (veja .env.example).",
        ) from exc


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Retorna a configuração carregada uma única vez por processo."""
    return load_settings()
