"""optimus commit."""

from __future__ import annotations

from typing import Annotated

import typer

from optimus_cyber.cli.commands._shared import run_intent
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.options import CommitType
from optimus_cyber.cli.validators import commit_scope
from optimus_cyber.core.models import Intent


@handle_errors
def commit(
    ctx: typer.Context,
    commit_type: Annotated[
        CommitType | None,
        typer.Option(
            "--type",
            "-t",
            help="Tipo do commit. Sem a opção, o agente sugere.",
            case_sensitive=False,
        ),
    ] = None,
    scope: Annotated[
        str | None,
        typer.Option("--scope", "-s", help="Escopo, ex.: cli, auth.", callback=commit_scope),
    ] = None,
) -> None:
    """Gera uma mensagem de commit semântica a partir do diff.

    O commit sempre exige sua confirmação antes de ser criado.

    Exemplo: [bold]optimus commit --type feat --scope cli[/]
    """
    run_intent(
        ctx,
        Intent.COMMIT,
        options={"type": commit_type.value if commit_type else None, "scope": scope},
    )
