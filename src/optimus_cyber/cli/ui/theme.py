"""Tema visual da CLI: todos os estilos ficam nomeados aqui."""

from rich.theme import Theme

from optimus_cyber.core.models import RiskLevel

OPTIMUS_THEME = Theme(
    {
        "brand": "bold cyan",
        "mode": "magenta",
        "muted": "dim",
        "label": "bold",
        "success": "bold green",
        "info": "cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "hint": "italic dim",
        "risk.read_only": "green",
        "risk.execute": "yellow",
        "risk.write": "bold yellow",
        "risk.destructive": "bold red",
        "risk.privileged": "bold white on red",
    }
)

RISK_LABELS: dict[RiskLevel, str] = {
    RiskLevel.READ_ONLY: "leitura",
    RiskLevel.EXECUTE: "execução",
    RiskLevel.WRITE: "escrita",
    RiskLevel.DESTRUCTIVE: "destrutiva",
    RiskLevel.PRIVILEGED: "privilegiada",
}
