"""CommandRouter: traduz comandos da CLI em ``UserRequest`` e os despacha."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from optimus_cyber.core.models import CommandOutcome, Intent, OptionValue, UserRequest


class RequestRunner(Protocol):
    """Contrato mínimo que a CLI espera da camada de orquestração."""

    async def run(self, request: UserRequest) -> CommandOutcome:
        """Executa a requisição e devolve o resultado."""
        ...


class CommandRouter:
    """Ponte entre a CLI (síncrona) e a orquestração (assíncrona)."""

    def __init__(self, runner: RequestRunner) -> None:
        self._runner = runner

    @staticmethod
    def build(
        intent: Intent,
        workspace: Path,
        *,
        text: str = "",
        options: Mapping[str, OptionValue] | None = None,
    ) -> UserRequest:
        """Cria a requisição, descartando opções não informadas."""
        cleaned: dict[str, OptionValue] = {
            key: value for key, value in (options or {}).items() if value is not None
        }
        return UserRequest(intent=intent, workspace=workspace, text=text, options=cleaned)

    def dispatch(self, request: UserRequest) -> CommandOutcome:
        """Executa a requisição no runner configurado."""
        return asyncio.run(self._runner.run(request))
