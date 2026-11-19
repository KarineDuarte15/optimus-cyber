"""optimus docs."""

from __future__ import annotations

from typing import Annotated

import typer

from optimus_cyber.cli.commands._shared import run_intent
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.options import DocsTarget
from optimus_cyber.core.models import Intent


@handle_errors
def docs(
    ctx: typer.Context,
    target: Annotated[
        DocsTarget,
        typer.Option("--target", "-t", help="O que documentar.", case_sensitive=False),
    ] = DocsTarget.README,
) -> None:
    """Atualiza a documentação a partir do código.

    Exemplo: [bold]optimus docs --target changelog[/]
    """
    run_intent(ctx, Intent.DOCS, options={"target": target.value})
