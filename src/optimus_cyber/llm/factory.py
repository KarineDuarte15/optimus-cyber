"""Fábrica de providers com registro extensível.

Para suportar um provider novo: implemente ``LLMProvider`` e chame
``register_provider``. Agentes e orquestrador não mudam.
"""

from __future__ import annotations

from collections.abc import Callable

from optimus_cyber.config.settings import API_KEY_ENV, AppSettings, ProviderName
from optimus_cyber.core.errors import ConfigError
from optimus_cyber.core.interfaces.llm import LLMProvider
from optimus_cyber.llm.config import ProviderConfig
from optimus_cyber.llm.retry import RetryingProvider

ProviderBuilder = Callable[[ProviderConfig], LLMProvider]


def _build_gemini(config: ProviderConfig) -> LLMProvider:
    from optimus_cyber.llm.gemini import GeminiProvider  # import tardio do SDK

    return GeminiProvider(config)


def _build_claude(config: ProviderConfig) -> LLMProvider:
    from optimus_cyber.llm.claude import ClaudeProvider  # import tardio do SDK

    return ClaudeProvider(config)


_REGISTRY: dict[ProviderName, ProviderBuilder] = {
    ProviderName.GEMINI: _build_gemini,
    ProviderName.CLAUDE: _build_claude,
}


def register_provider(name: ProviderName, builder: ProviderBuilder) -> None:
    """Registra (ou substitui) o construtor de um provider."""
    _REGISTRY[name] = builder


def registered_providers() -> tuple[ProviderName, ...]:
    """Providers disponíveis."""
    return tuple(_REGISTRY)


def create_provider(settings: AppSettings, name: ProviderName | None = None) -> LLMProvider:
    """Cria o provider pedido (ou o principal), já com retry.

    Raises:
        ConfigError: provider sem construtor registrado ou sem chave de API.
    """
    provider = name or settings.primary_provider
    builder = _REGISTRY.get(provider)
    if builder is None:
        raise ConfigError(f"Provider '{provider}' não está registrado.")

    api_key = settings.api_key_for(provider)
    if api_key is None:
        env_name = API_KEY_ENV[provider]
        raise ConfigError(
            f"Chave de API do {provider.value} não configurada.",
            hint=f"Defina {env_name} no arquivo .env (veja .env.example).",
        )

    config = ProviderConfig(
        model=settings.model_for(provider),
        api_key=api_key,
        timeout_seconds=settings.request_timeout_seconds,
    )
    return RetryingProvider(
        builder(config),
        max_retries=settings.max_retries,
        base_delay=settings.retry_base_delay_seconds,
    )
