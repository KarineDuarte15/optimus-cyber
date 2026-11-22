"""optimus status."""

from __future__ import annotations

import typer

from optimus_cyber import __version__
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.state import get_state
from optimus_cyber.config.settings import ProviderName, load_settings


@handle_errors
def status(ctx: typer.Context) -> None:
    """Mostra a configuração ativa, sem revelar segredos."""
    state = get_state(ctx)
    settings = load_settings()
    primary = settings.primary_provider

    rows = {
        "Versão": __version__,
        "Projeto": str(state.workspace),
        "Provider": f"{primary.value} ({settings.model_for(primary)})",
        "Provider secundário": str(settings.secondary_provider or "nenhum"),
        "Temperatura": f"{settings.temperature:g}",
        "Máx. tokens de saída": str(settings.max_output_tokens),
        "Timeout": f"{settings.request_timeout_seconds:g} s",
        "Tentativas extras": str(settings.max_retries),
    }
    for provider in ProviderName:
        rows[f"Chave {provider.value}"] = (
            "configurada" if settings.has_key_for(provider) else "ausente"
        )
    rows["Logs"] = str(settings.log_file) if settings.log_file else "somente com --debug"
    state.presenter.key_values("Optimus Cyber — status", rows)
