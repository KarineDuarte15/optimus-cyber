"""Adaptador do Google Gemini (SDK ``google-genai``)."""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from optimus_cyber.core.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from optimus_cyber.core.interfaces.llm import ProviderCapabilities
from optimus_cyber.core.models.llm import (
    FinishReason,
    LLMRequest,
    LLMResponse,
    Role,
    TokenUsage,
)
from optimus_cyber.llm.base import SDKProvider
from optimus_cyber.llm.config import ProviderConfig

PROVIDER_NAME = "gemini"

MODELS_HINT = "Para ver os modelos disponíveis, consulte a seção 'Modelos' do README."
UNAVAILABLE_HINT = (
    "O modelo pode estar sobrecarregado. Tente de novo em instantes ou use outro "
    "modelo em OPTIMUS_MODEL (ex.: gemini-3.5-flash)."
)

_ROLES: dict[Role, str] = {Role.USER: "user", Role.ASSISTANT: "model"}

_FINISH: dict[str, FinishReason] = {
    "STOP": FinishReason.STOP,
    "MAX_TOKENS": FinishReason.LENGTH,
    "SAFETY": FinishReason.SAFETY,
    "RECITATION": FinishReason.SAFETY,
    "BLOCKLIST": FinishReason.SAFETY,
    "PROHIBITED_CONTENT": FinishReason.SAFETY,
    "SPII": FinishReason.SAFETY,
    "IMAGE_SAFETY": FinishReason.SAFETY,
}


def build_client(config: ProviderConfig) -> genai.Client:
    """Cria o cliente com timeout e sem retry interno (o retry é nosso)."""
    return genai.Client(
        api_key=config.api_key.get_secret_value(),
        http_options=types.HttpOptions(
            timeout=int(config.timeout_seconds * 1000),
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


class GeminiProvider(SDKProvider):
    """Provider principal do Optimus Cyber."""

    def __init__(self, config: ProviderConfig, *, client: Any | None = None) -> None:
        super().__init__(config)
        self._client = client if client is not None else build_client(config)

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_temperature=True, max_output_tokens=65536)

    async def _send(self, request: LLMRequest) -> LLMResponse:
        contents = [
            types.Content(role=_ROLES[message.role], parts=[types.Part(text=message.content)])
            for message in request.conversation
        ]
        config = types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )
        raw = await self._client.aio.models.generate_content(
            model=self.model, contents=contents, config=config
        )
        return self._parse(raw)

    def _parse(self, raw: types.GenerateContentResponse) -> LLMResponse:
        feedback = raw.prompt_feedback
        if feedback is not None and feedback.block_reason is not None:
            raise ProviderResponseError(
                f"O Gemini bloqueou o pedido ({_enum_name(feedback.block_reason)}).",
                provider=PROVIDER_NAME,
                hint="Reformule o pedido ou remova conteúdo sensível.",
            )
        if not raw.candidates:
            raise ProviderResponseError("O Gemini não devolveu resposta.", provider=PROVIDER_NAME)

        candidate = raw.candidates[0]
        finish = _FINISH.get(_enum_name(candidate.finish_reason), FinishReason.OTHER)
        parts = candidate.content.parts if candidate.content and candidate.content.parts else []
        text = "".join(part.text for part in parts if part.text and not part.thought)

        if not text:
            hint = None
            if finish is FinishReason.LENGTH:
                hint = (
                    "O limite de tokens acabou antes do texto (o raciocínio do modelo "
                    "também consome tokens). Aumente OPTIMUS_MAX_OUTPUT_TOKENS."
                )
            raise ProviderResponseError(
                f"O Gemini devolveu resposta vazia (motivo: {finish.value}).",
                provider=PROVIDER_NAME,
                hint=hint,
            )

        usage = raw.usage_metadata
        return LLMResponse(
            content=text,
            finish_reason=finish,
            usage=TokenUsage(
                input_tokens=(usage.prompt_token_count or 0) if usage else 0,
                output_tokens=(usage.candidates_token_count or 0) if usage else 0,
                reasoning_tokens=(usage.thoughts_token_count or 0) if usage else 0,
            ),
            provider=PROVIDER_NAME,
            model=raw.model_version or self.model,
            requested_model=self.model,
        )

    def _translate_error(self, exc: Exception) -> ProviderError:
        if isinstance(exc, genai_errors.APIError):
            return _from_status(exc.code, exc.status, self.model)
        return super()._translate_error(exc)


def _enum_name(value: object) -> str:
    return str(getattr(value, "name", value))


def _from_status(code: int | None, status: str | None, model: str) -> ProviderError:
    label = f"HTTP {code}" + (f" {status}" if status else "")
    if code in (401, 403):
        return ProviderAuthError(
            f"O Gemini recusou a chave de API ({label}).",
            provider=PROVIDER_NAME,
            status_code=code,
            hint="Confira GEMINI_API_KEY no .env e se a chave está ativa.",
        )
    if code == 429:
        return ProviderRateLimitError(
            f"Limite de uso do Gemini atingido ({label}).",
            provider=PROVIDER_NAME,
            status_code=code,
            hint="Aguarde alguns instantes ou verifique a cota do projeto.",
        )
    if code == 404:
        return ProviderRequestError(
            f"O modelo '{model}' não existe ou não está liberado para esta chave ({label}).",
            provider=PROVIDER_NAME,
            status_code=code,
            hint=f"Ajuste OPTIMUS_MODEL no .env. {MODELS_HINT}",
        )
    if code is not None and code >= 500:
        return ProviderUnavailableError(
            f"O Gemini está indisponível para o modelo '{model}' ({label}).",
            provider=PROVIDER_NAME,
            status_code=code,
            hint=UNAVAILABLE_HINT,
        )
    return ProviderRequestError(
        f"O Gemini rejeitou a requisição ({label}).",
        provider=PROVIDER_NAME,
        status_code=code,
        hint="Confira o nome do modelo em OPTIMUS_MODEL e os parâmetros.",
    )
