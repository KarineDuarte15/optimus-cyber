"""optimus ask."""

from __future__ import annotations

from typing import Annotated

import typer

from optimus_cyber.cli.commands._shared import run_intent
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.validators import question_text
from optimus_cyber.core.models import Intent


@handle_errors
def ask(
    ctx: typer.Context,
    question: Annotated[
        str,
        typer.Argument(
            help="Pergunta sobre o projeto, entre aspas.",
            callback=question_text,
            show_default=False,
        ),
    ],
) -> None:
    """Faz uma pergunta sobre o projeto.

    Exemplo: [bold]optimus ask "onde a autenticação é validada?"[/]
    """
    run_intent(ctx, Intent.ASK, text=question)
