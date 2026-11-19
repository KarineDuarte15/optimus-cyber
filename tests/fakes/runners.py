"""Runners falsos para testar a CLI sem a camada de orquestração."""

from __future__ import annotations

from optimus_cyber.core.models import (
    CommandOutcome,
    OutcomeStatus,
    PlannedStep,
    UserRequest,
)


class RecordingRunner:
    """Guarda as requisições recebidas e devolve um resultado fixo."""

    def __init__(self, status: OutcomeStatus = OutcomeStatus.COMPLETED) -> None:
        self.requests: list[UserRequest] = []
        self.status = status

    async def run(self, request: UserRequest) -> CommandOutcome:
        self.requests.append(request)
        return CommandOutcome(
            request_id=request.id,
            intent=request.intent,
            status=self.status,
            summary="resultado de teste",
            steps=(PlannedStep(order=1, agent="Fake", description="passo de teste"),),
        )


class FailingRunner:
    """Lança a exceção configurada."""

    def __init__(self, error: BaseException) -> None:
        self.error = error

    async def run(self, request: UserRequest) -> CommandOutcome:
        raise self.error
