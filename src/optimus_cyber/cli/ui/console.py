"""Fábrica dos consoles Rich usados pelo Presenter."""

from __future__ import annotations

from rich.console import Console

from optimus_cyber.cli.ui.theme import OPTIMUS_THEME


def build_consoles(*, no_color: bool = False) -> tuple[Console, Console]:
    """Cria os consoles de saída padrão e de erro com o tema do Optimus."""
    stdout = Console(theme=OPTIMUS_THEME, no_color=no_color, highlight=False)
    stderr = Console(theme=OPTIMUS_THEME, no_color=no_color, highlight=False, stderr=True)
    return stdout, stderr
