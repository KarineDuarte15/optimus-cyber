"""optimus test (módulo chamado testing para não ser confundido com testes)."""

from __future__ import annotations

from typing import Annotated

import typer

from optimus_cyber.cli.commands._shared import run_intent
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.validators import clean_text
from optimus_cyber.core.models import Intent


@handle_errors
def run_tests(
    ctx: typer.Context,
    keyword: Annotated[
        str | None,
        typer.Option("--keyword", "-k", help="Filtra testes pelo nome.", callback=clean_text),
    ] = None,
    coverage: Annotated[
        bool, typer.Option("--coverage", help="Inclui relatório de cobertura.")
    ] = False,
    fail_fast: Annotated[
        bool, typer.Option("--fail-fast", "-x", help="Para no primeiro teste que falhar.")
    ] = False,
) -> None:
    """Executa os testes do projeto e interpreta as falhas.

    Exemplo: [bold]optimus test -k login --coverage[/]
    """
    run_intent(
        ctx,
        Intent.TEST,
        options={"keyword": keyword, "coverage": coverage, "fail_fast": fail_fast},
    )
