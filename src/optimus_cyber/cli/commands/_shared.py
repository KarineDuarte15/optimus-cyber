"""Fluxo comum a todos os comandos de engenharia.

Cabeçalho → resumo da entrada → execução com spinner → resultado.
"""

from __future__ import annotations

from collections.abc import Mapping

import typer

from optimus_cyber.cli.state import get_state
from optimus_cyber.cli.ui.labels import MODE_LABELS, WORKING_LABELS
from optimus_cyber.core.models import Intent, OptionValue


def _format(value: OptionValue) -> str:
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, tuple):
        return ", ".join(value) or "—"
    return str(value)


def run_intent(
    ctx: typer.Context,
    intent: Intent,
    *,
    text: str = "",
    options: Mapping[str, OptionValue] | None = None,
) -> None:
    """Executa uma intenção e apresenta o resultado."""
    state = get_state(ctx)
    presenter = state.presenter
    request = state.router.build(intent, state.workspace, text=text, options=options)

    presenter.header(MODE_LABELS[intent])
    summary = {"Projeto": str(request.workspace)}
    if request.text:
        summary["Entrada"] = request.text
    summary.update({key: _format(value) for key, value in request.options.items()})
    presenter.key_values("Requisição", summary)

    with presenter.working(WORKING_LABELS[intent]):
        outcome = state.router.dispatch(request)
    presenter.outcome(outcome)
