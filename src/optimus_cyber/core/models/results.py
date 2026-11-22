"""Resultado de um comando e passos planejados."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from optimus_cyber.core.models.base import DomainModel
from optimus_cyber.core.models.llm import LLMResponse
from optimus_cyber.core.models.requests import Intent


class RiskLevel(StrEnum):
    """Nível de risco de uma ação, usado pela política de permissões."""

    READ_ONLY = "read_only"
    EXECUTE = "execute"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    PRIVILEGED = "privileged"


class PlannedStep(DomainModel):
    """Um passo que o agente executará."""

    order: int = Field(ge=1)
    agent: str
    description: str
    risk: RiskLevel = RiskLevel.READ_ONLY


class OutcomeStatus(StrEnum):
    """Estado final de um comando."""

    PREVIEW = "preview"
    COMPLETED = "completed"
    FAILED = "failed"


class CommandOutcome(DomainModel):
    """O que a camada de execução devolve para a CLI renderizar."""

    request_id: UUID
    intent: Intent
    status: OutcomeStatus
    summary: str
    steps: tuple[PlannedStep, ...] = ()
    notes: tuple[str, ...] = ()
    response: LLMResponse | None = None
