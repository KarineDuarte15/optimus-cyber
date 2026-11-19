"""Aplicação Typer: ponto de entrada do comando ``optimus``.

Este módulo só faz a composição: opções globais, estado da execução e
registro dos comandos. Cada comando vive em ``cli/commands``.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer

from optimus_cyber import __version__
from optimus_cyber.cli.commands.ask import ask
from optimus_cyber.cli.commands.commit import commit
from optimus_cyber.cli.commands.docs import docs
from optimus_cyber.cli.commands.doctor import doctor
from optimus_cyber.cli.commands.explain import explain
from optimus_cyber.cli.commands.fix import fix
from optimus_cyber.cli.commands.project import project
from optimus_cyber.cli.commands.review import review
from optimus_cyber.cli.commands.status import status
from optimus_cyber.cli.commands.testing import run_tests
from optimus_cyber.cli.state import AppState
from optimus_cyber.cli.ui.presenter import Presenter

app = typer.Typer(
    name="optimus",
    help="[bold cyan]Optimus Cyber[/] — agente de engenharia de software no terminal.",
    epilog="Use [bold]optimus COMANDO --help[/] para ver as opções de cada comando.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

PANEL_DIAGNOSIS = "Diagnóstico"
PANEL_CODE = "Código"
PANEL_GIT_DOCS = "Git e documentação"
PANEL_PROJECT = "Projeto"

app.command("ask", rich_help_panel=PANEL_PROJECT)(ask)
app.command("project", rich_help_panel=PANEL_PROJECT)(project)
app.command("status", rich_help_panel=PANEL_PROJECT)(status)
app.command("doctor", rich_help_panel=PANEL_DIAGNOSIS)(doctor)
app.command("explain", rich_help_panel=PANEL_DIAGNOSIS)(explain)
app.command("fix", rich_help_panel=PANEL_CODE)(fix)
app.command("review", rich_help_panel=PANEL_CODE)(review)
app.command("test", rich_help_panel=PANEL_CODE)(run_tests)
app.command("commit", rich_help_panel=PANEL_GIT_DOCS)(commit)
app.command("docs", rich_help_panel=PANEL_GIT_DOCS)(docs)


def _version_callback(value: bool) -> None:
    if value:
        Presenter.create().version(__version__)
        raise typer.Exit()


@app.callback()
def root(
    ctx: typer.Context,
    path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-C",
            help="Pasta do projeto. Padrão: pasta atual.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            show_default=False,
        ),
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", help="Mostra detalhes técnicos de erros.")
    ] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Desativa cores.")] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Mostra a versão e sai.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Monta o estado da execução (ou reaproveita um estado injetado em testes)."""
    workspace = path or Path.cwd()
    if isinstance(ctx.obj, AppState):
        ctx.obj = replace(ctx.obj, workspace=workspace, debug=debug or ctx.obj.debug)
    else:
        ctx.obj = AppState.default(workspace=workspace, debug=debug, no_color=no_color)


def main() -> None:
    """Executa a aplicação Typer."""
    app()
