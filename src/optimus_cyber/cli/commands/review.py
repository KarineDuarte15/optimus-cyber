"""optimus review."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from optimus_cyber.cli.commands._shared import run_intent
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.options import ReviewFocus
from optimus_cyber.cli.validators import mutually_exclusive
from optimus_cyber.core.models import Intent


@handle_errors
def review(
    ctx: typer.Context,
    paths: Annotated[
        list[Path] | None,
        typer.Argument(
            help="Arquivos ou pastas a revisar. Sem argumentos, revisa o diff atual.",
            exists=True,
            resolve_path=True,
            show_default=False,
        ),
    ] = None,
    focus: Annotated[
        ReviewFocus,
        typer.Option("--focus", "-f", help="Aspecto principal da revisão.", case_sensitive=False),
    ] = ReviewFocus.ALL,
    staged: Annotated[
        bool,
        typer.Option("--staged", help="Revisa só as alterações em stage no Git."),
    ] = False,
) -> None:
    """Revisa código: qualidade, segurança, desempenho e arquitetura.

    Exemplo: [bold]optimus review src/app --focus security[/]
    """
    mutually_exclusive(**{"CAMINHOS": paths or None, "--staged": staged})
    run_intent(
        ctx,
        Intent.REVIEW,
        options={
            "paths": tuple(str(path) for path in paths) if paths else None,
            "focus": focus.value,
            "staged": staged,
        },
    )
