"""optimus fix."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from optimus_cyber.cli.commands._shared import run_intent
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.validators import clean_text, require_any
from optimus_cyber.core.models import Intent


@handle_errors
def fix(
    ctx: typer.Context,
    issue: Annotated[
        str | None,
        typer.Option("--issue", "-i", help="Descrição do problema.", callback=clean_text),
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
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Só mostra o patch, sem aplicar."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes", "-y", help="Aprova automaticamente ações de escrita (nunca destrutivas)."
        ),
    ] = False,
) -> None:
    """Corrige um problema: diagnóstico, patch, aprovação e testes.

    Exemplo: [bold]optimus fix --issue "API retorna 500 no /login"[/]
    """
    require_any(**{"--issue": issue, "--log": log})
    run_intent(
        ctx,
        Intent.FIX,
        text=issue or "",
        options={"log": str(log) if log else None, "dry_run": dry_run, "auto_approve": yes},
    )
