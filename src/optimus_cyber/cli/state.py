"""Estado compartilhado entre o callback global e os comandos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer

from optimus_cyber.cli.router import CommandRouter
from optimus_cyber.cli.ui.presenter import Presenter
from optimus_cyber.config.settings import get_settings
from optimus_cyber.llm.service import LLMService
from optimus_cyber.orchestration.orchestrator import DefaultOrchestrator


@dataclass(frozen=True)
class AppState:
    """Dependências da execução atual, montadas uma vez por invocação."""

    presenter: Presenter
    router: CommandRouter
    workspace: Path
    debug: bool = False

    @classmethod
    def default(cls, *, workspace: Path, debug: bool, no_color: bool) -> AppState:
        """Composição padrão (produção)."""
        return cls(
            presenter=Presenter.create(no_color=no_color),
            router=CommandRouter(
                DefaultOrchestrator(lambda: LLMService.from_settings(get_settings()))
            ),
            workspace=workspace,
            debug=debug,
        )


def get_state(ctx: typer.Context) -> AppState:
    """Recupera o estado montado pelo callback global."""
    state = getattr(ctx, "obj", None)
    if not isinstance(state, AppState):
        raise RuntimeError("Estado da CLI não inicializado.")
    return state
