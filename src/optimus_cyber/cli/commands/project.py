"""optimus project."""

from __future__ import annotations

from typing import Annotated

import typer

from optimus_cyber.cli.commands._shared import run_intent
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.core.models import Intent

MAX_DEPTH = 6


@handle_errors
def project(
    ctx: typer.Context,
    depth: Annotated[
        int,
        typer.Option(
            "--depth", "-d", help="Profundidade da árvore de diretórios.", min=1, max=MAX_DEPTH
        ),
    ] = 2,
) -> None:
    """Explica o projeto: arquitetura, dependências, Docker e CI/CD.

    Exemplo: [bold]optimus project --depth 3[/]
    """
    run_intent(ctx, Intent.PROJECT, options={"depth": depth})
