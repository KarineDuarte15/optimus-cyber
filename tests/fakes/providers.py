"""Providers falsos: registram pedidos e devolvem respostas roteirizadas."""

from __future__ import annotations

from collections.abc import Iterable

from optimus_cyber.core.interfaces.llm import LLMProvider, ProviderCapabilities
from optimus_cyber.core.models.llm import FinishReason, LLMRequest, LLMResponse, TokenUsage


def make_response(
    content: str = "resposta falsa",
    *,
    finish: FinishReason = FinishReason.STOP,
    provider: str = "fake",
) -> LLMResponse:
    return LLMResponse(
        content=content,
        finish_reason=finish,
        usage=TokenUsage(input_tokens=10, output_tokens=5),
        provider=provider,
        model="fake-model",
        latency_ms=42,
    )


class FakeProvider(LLMProvider):
    """Devolve, em ordem, respostas ou exceções da fila; repete a última resposta."""

    def __init__(
        self,
        script: Iterable[LLMResponse | BaseException] = (),
        *,
        supports_temperature: bool = True,
    ) -> None:
        self._script = list(script) or [make_response()]
        self._supports_temperature = supports_temperature
        self.requests: list[LLMRequest] = []

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-model"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_temperature=self._supports_temperature)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        item = self._script.pop(0) if len(self._script) > 1 else self._script[0]
        if isinstance(item, BaseException):
            raise item
        return item
