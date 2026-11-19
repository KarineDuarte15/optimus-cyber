"""Presenter: único ponto da aplicação que escreve no terminal.

Comandos descrevem *o que* mostrar chamando métodos daqui; o *como*
(cores, painéis, tabelas) fica concentrado neste módulo e no tema.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from optimus_cyber.cli.ui.console import build_consoles
from optimus_cyber.cli.ui.labels import APP_TITLE
from optimus_cyber.cli.ui.theme import RISK_LABELS
from optimus_cyber.core.models import CommandOutcome, OutcomeStatus


class Presenter:
    """Componentes visuais reutilizáveis da CLI."""

    def __init__(self, console: Console, error_console: Console) -> None:
        self.console = console
        self.error_console = error_console

    @classmethod
    def create(cls, *, no_color: bool = False) -> Presenter:
        """Cria um Presenter com os consoles padrão."""
        stdout, stderr = build_consoles(no_color=no_color)
        return cls(stdout, stderr)

    # ------------------------------------------------------------ cabeçalho
    def version(self, version: str) -> None:
        """Mostra a versão instalada."""
        self.console.print(f"[brand]optimus-cyber[/] {version}")

    def header(self, mode: str) -> None:
        """Painel de abertura com o nome da ferramenta e o modo ativo."""
        title = Text(APP_TITLE, style="brand")
        content = Text.assemble(title, "\n", Text(mode, style="mode"))
        self.console.print(Panel(content, box=box.ROUNDED, expand=False, border_style="brand"))

    # ------------------------------------------------------------ progresso
    @contextmanager
    def working(self, message: str) -> Iterator[None]:
        """Mostra um spinner enquanto o bloco executa e confirma ao final."""
        with self.console.status(Text(message, style="info"), spinner="dots"):
            yield
        self.console.print(f"[success]✓[/] {message}")

    # ------------------------------------------------------------ conteúdo
    def key_values(self, title: str, rows: Mapping[str, str]) -> None:
        """Tabela de duas colunas (rótulo e valor)."""
        table = Table(title=title, title_justify="left", show_header=False, box=box.SIMPLE)
        table.add_column(style="label", no_wrap=True)
        table.add_column(overflow="fold")
        for key, value in rows.items():
            table.add_row(key, value)
        self.console.print(table)

    def outcome(self, outcome: CommandOutcome) -> None:
        """Renderiza o resultado de um comando: resumo, plano e notas."""
        self.console.print(f"\n[label]Objetivo:[/] {outcome.summary}")
        if outcome.steps:
            table = Table(title="Plano de execução", title_justify="left", box=box.SIMPLE_HEAD)
            table.add_column("#", justify="right", style="muted")
            table.add_column("Agente", style="info", no_wrap=True)
            table.add_column("Ação", overflow="fold")
            table.add_column("Risco", no_wrap=True)
            for step in outcome.steps:
                risk = Text(RISK_LABELS[step.risk], style=f"risk.{step.risk.value}")
                table.add_row(str(step.order), step.agent, step.description, risk)
            self.console.print(table)
        if outcome.status is OutcomeStatus.PREVIEW:
            body = Group(*(Text(note) for note in outcome.notes))
            self.console.print(Panel(body, title="Em desenvolvimento", border_style="warning"))
        elif outcome.status is OutcomeStatus.COMPLETED:
            self.success("Concluído.")
        else:
            self.error("O comando terminou com falha.")

    # ------------------------------------------------------------ mensagens
    def success(self, message: str) -> None:
        """Mensagem de sucesso."""
        self.console.print(f"[success]✓[/] {message}")

    def info(self, message: str) -> None:
        """Mensagem informativa."""
        self.console.print(f"[info]•[/] {message}")

    def warning(self, message: str) -> None:
        """Aviso, enviado para stderr."""
        self.error_console.print(f"[warning]![/] {message}")

    def error(self, message: str, *, hint: str | None = None) -> None:
        """Erro com dica opcional, enviado para stderr."""
        content = Text(message)
        if hint:
            content.append("\n")
            content.append(hint, style="hint")
        self.error_console.print(
            Panel(content, title="Erro", title_align="left", border_style="error", expand=False)
        )

    def exception(self) -> None:
        """Traceback detalhado (somente com --debug)."""
        self.error_console.print_exception(show_locals=False)
