"""Adaptador do Anthropic Claude (SDK ``anthropic``)."""

from __future__ import annotations

from typing import Any

import anthropic

from optimus_cyber.core.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from optimus_cyber.core.interfaces.llm import ProviderCapabilities
from optimus_cyber.core.models.llm import FinishReason, LLMRequest, LLMResponse, TokenUsage
from optimus_cyber.llm.base import SDKProvider
from optimus_cyber.llm.config import ProviderConfig

PROVIDER_NAME = "claude"
DEFAULT_MAX_TOKENS = 4096  # a API do Claude exige max_tokens

_FINISH: dict[str, FinishReason] = {
    "end_turn": FinishReason.STOP,
    "stop_sequence": FinishReason.STOP,
    "max_tokens": FinishReason.LENGTH,
    "model_context_window_exceeded": FinishReason.LENGTH,
    "refusal": FinishReason.SAFETY,
}


def build_client(config: ProviderConfig) -> anthropic.AsyncAnthropic:
    """Cria o cliente com timeout e sem retry interno (o retry é nosso)."""
    return anthropic.AsyncAnthropic(
        api_key=config.api_key.get_secret_value(),
        timeout=config.timeout_seconds,
        max_retries=0,
    )


class ClaudeProvider(SDKProvider):
    """Provider secundário do Optimus Cyber."""

    def __init__(self, config: ProviderConfig, *, client: Any | None = None) -> None:
        super().__init__(config)
        self._client = client if client is not None else build_client(config)

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def capabilities(self) -> ProviderCapabilities:
        # A API atual de Messages não aceita o parâmetro temperature.
        return ProviderCapabilities(supports_temperature=False)

    async def _send(self, request: LLMRequest) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_output_tokens or DEFAULT_MAX_TOKENS,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in request.conversation
            ],
        }
        if request.system_prompt:
            kwargs["system"] = request.system_prompt
        raw = await self._client.messages.create(**kwargs)
        return self._parse(raw)

    def _parse(self, raw: Any) -> LLMResponse:
        text = "".join(
            block.text for block in raw.content if getattr(block, "type", None) == "text"
        )
        finish = _FINISH.get(str(raw.stop_reason), FinishReason.OTHER)
        if not text:
            raise ProviderResponseError(
                f"O Claude devolveu resposta vazia (motivo: {raw.stop_reason}).",
                provider=PROVIDER_NAME,
            )
        usage = raw.usage
        return LLMResponse(
            content=text,
            finish_reason=finish,
            usage=TokenUsage(
                input_tokens=usage.input_tokens or 0,
                output_tokens=usage.output_tokens or 0,
            ),
            provider=PROVIDER_NAME,
            model=raw.model or self.model,
            requested_model=self.model,
        )

    def _translate_error(self, exc: Exception) -> ProviderError:
        if isinstance(exc, anthropic.APITimeoutError):
            return ProviderTimeoutError(
                "O Claude não respondeu dentro do timeout.", provider=PROVIDER_NAME
            )
        if isinstance(exc, anthropic.APIConnectionError):
            return ProviderUnavailableError(
                "Falha de conexão com o Claude.",
                provider=PROVIDER_NAME,
                hint="Verifique a internet, proxy ou firewall.",
            )
        if isinstance(exc, anthropic.APIStatusError):
            return _from_status(exc.status_code, _retry_after(exc), self.model)
        return super()._translate_error(exc)


def _retry_after(exc: anthropic.APIStatusError) -> float | None:
    value = exc.response.headers.get("retry-after") if exc.response is not None else None
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _from_status(code: int, retry_after: float | None, model: str) -> ProviderError:
    label = f"HTTP {code}"
    if code in (401, 403):
        return ProviderAuthError(
            f"O Claude recusou a chave de API ({label}).",
            provider=PROVIDER_NAME,
            status_code=code,
            hint="Confira ANTHROPIC_API_KEY no .env e se a chave está ativa.",
        )
    if code == 429:
        return ProviderRateLimitError(
            f"Limite de uso do Claude atingido ({label}).",
            provider=PROVIDER_NAME,
            status_code=code,
            retry_after_seconds=retry_after,
        )
    if code == 404:
        return ProviderRequestError(
            f"O modelo '{model}' não existe ou não está liberado para esta chave ({label}).",
            provider=PROVIDER_NAME,
            status_code=code,
            hint="Ajuste OPTIMUS_MODEL no .env com um modelo Claude válido.",
        )
    if code >= 500:  # inclui 529 (sobrecarga)
        return ProviderUnavailableError(
            f"O Claude está indisponível para o modelo '{model}' ({label}).",
            provider=PROVIDER_NAME,
            status_code=code,
            retry_after_seconds=retry_after,
            hint="O serviço pode estar sobrecarregado. Tente de novo em instantes.",
        )
    return ProviderRequestError(
        f"O Claude rejeitou a requisição ({label}).",
        provider=PROVIDER_NAME,
        status_code=code,
        hint="Confira o nome do modelo em OPTIMUS_MODEL e os parâmetros.",
    )
