"""optimus explain."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from optimus_cyber.cli.commands._shared import run_intent
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.validators import clean_text, mutually_exclusive, require_any
from optimus_cyber.core.models import Intent


@handle_errors
def explain(
    ctx: typer.Context,
    error: Annotated[
        str | None,
        typer.Argument(
            help="Mensagem de erro ou stacktrace, entre aspas.",
            callback=clean_text,
            show_default=False,
        ),
    ] = None,
    log: Annotated[
        Path | None,
        typer.Option(
            "--log",
            "-l",
            help="Arquivo de log com o erro.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """Explica um erro: causa, arquivo, linha e alternativas.

    Exemplo: [bold]optimus explain "KeyError: 'user_id'"[/]
    """
    require_any(**{"ERRO": error, "--log": log})
    mutually_exclusive(**{"ERRO": error, "--log": log})
    run_intent(
        ctx,
        Intent.EXPLAIN,
        text=error or "",
        options={"log": str(log) if log else None},
    )
