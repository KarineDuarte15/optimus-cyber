"""Aplicação Typer: ponto de entrada do comando ``optimus``.

Nesta etapa a CLI expõe apenas ``--version`` e ``status``. Os comandos
de engenharia (doctor, explain, fix...) chegam nas próximas etapas.
"""

from __future__ import annotations

from typing import Annotated

import typer
from pydantic import ValidationError
from rich.table import Table

from optimus_cyber import __version__
from optimus_cyber.cli.ui.console import console, error_console
from optimus_cyber.config.settings import AppSettings, ProviderName

app = typer.Typer(
    name="optimus",
    help="Optimus Cyber: agente de engenharia de software no terminal.",
    no_args_is_help=True,
    add_completion=False,
)

EXIT_CONFIG_ERROR = 3


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"optimus-cyber {__version__}")
        raise typer.Exit()


@app.callback()
def root(
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
    """Optimus Cyber: agente de engenharia de software no terminal."""


@app.command()
def status() -> None:
    """Mostra a configuração ativa, sem revelar segredos."""
    try:
        settings = AppSettings()
    except ValidationError as exc:
        error_console.print(f"[bold red]Configuração inválida:[/]\n{exc}")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from exc

    table = Table(title="Optimus Cyber — status", show_header=False)
    table.add_column("Item", style="bold")
    table.add_column("Valor")
    table.add_row("Versão", __version__)
    table.add_row("Provider principal", f"{settings.primary_provider} ({settings.primary_model})")
    secondary = settings.secondary_provider or "nenhum"
    table.add_row("Provider secundário", str(secondary))
    for provider in ProviderName:
        configured = settings.has_key_for(provider)
        label = "[green]configurada[/]" if configured else "[yellow]ausente[/]"
        table.add_row(f"Chave {provider.value}", label)
    table.add_row("Nível de log", settings.log_level.value)
    console.print(table)


def main() -> None:
    """Executa a aplicação Typer."""
    app()
