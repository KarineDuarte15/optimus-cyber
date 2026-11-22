"""Orquestrador atual: ``ask`` usa o LLM; os demais comandos ainda são prévia.

O provider é criado só quando um comando precisa dele, então comandos que
não usam LLM funcionam mesmo sem chave de API configurada.
"""

from __future__ import annotations

from collections.abc import Callable

from optimus_cyber.core.models import (
    CommandOutcome,
    Intent,
    OutcomeStatus,
    UserRequest,
)
from optimus_cyber.llm.service import LLMService
from optimus_cyber.orchestration.stub import StubOrchestrator

ServiceFactory = Callable[[], LLMService]

ASK_SYSTEM_PROMPT = (
    "Você é o Optimus Cyber, um engenheiro de software sênior que ajuda no terminal. "
    "Responda em português do Brasil, de forma direta e técnica, em Markdown. "
    "Você ainda não tem acesso aos arquivos do projeto do usuário: quando a resposta "
    "depender do código dele, diga isso e explique o que verificar. "
    "Nunca invente nomes de arquivos, funções ou APIs."
)

ASK_NOTE = "Ainda sem leitura do projeto: a resposta usa só o conhecimento do modelo."


class DefaultOrchestrator:
    """Despacha cada intenção para quem sabe executá-la."""

    def __init__(
        self,
        service_factory: ServiceFactory,
        fallback: StubOrchestrator | None = None,
    ) -> None:
        self._service_factory = service_factory
        self._fallback = fallback or StubOrchestrator()

    async def run(self, request: UserRequest) -> CommandOutcome:
        if request.intent is Intent.ASK:
            return await self._ask(request)
        return await self._fallback.run(request)

    async def _ask(self, request: UserRequest) -> CommandOutcome:
        service = self._service_factory()
        response = await service.generate(request.text, system=ASK_SYSTEM_PROMPT)
        return CommandOutcome(
            request_id=request.id,
            intent=request.intent,
            status=OutcomeStatus.COMPLETED,
            summary="Responder uma pergunta",
            notes=(ASK_NOTE,),
            response=response,
        )
