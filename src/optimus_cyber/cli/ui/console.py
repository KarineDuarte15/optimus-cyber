"""Consoles Rich compartilhados pela CLI."""

from rich.console import Console

console = Console()
error_console = Console(stderr=True)
