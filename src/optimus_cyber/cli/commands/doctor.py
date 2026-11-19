"""optimus doctor."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from optimus_cyber.cli.commands._shared import run_intent
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.validators import clean_text, mutually_exclusive
from optimus_cyber.core.models import Intent


@handle_errors
def doctor(
    ctx: typer.Context,
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
    command: Annotated[
        str | None,
        typer.Option(
            "--cmd",
            "-c",
            help="Comando que reproduz o erro (ainda não é executado).",
            callback=clean_text,
        ),
    ] = None,
) -> None:
    """Diagnostica um erro a partir de um log ou de um comando.

    Sem opções, faz um diagnóstico geral do projeto.

    Exemplo: [bold]optimus doctor --log logs/app.log[/]
    """
    mutually_exclusive(**{"--log": log, "--cmd": command})
    run_intent(
        ctx,
        Intent.DIAGNOSE,
        options={"log": str(log) if log else None, "cmd": command},
    )
