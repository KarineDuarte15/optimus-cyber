"""optimus status."""

from __future__ import annotations

import typer
from pydantic import ValidationError

from optimus_cyber import __version__
from optimus_cyber.cli.errors import handle_errors
from optimus_cyber.cli.state import get_state
from optimus_cyber.config.settings import AppSettings, ProviderName
from optimus_cyber.core.errors import ConfigError


@handle_errors
def status(ctx: typer.Context) -> None:
    """Mostra a configuração ativa, sem revelar segredos."""
    state = get_state(ctx)
    try:
        settings = AppSettings()
    except ValidationError as exc:
        fields = ", ".join(str(err["loc"][0]) for err in exc.errors() if err["loc"])
        raise ConfigError(
            f"Configuração inválida: {fields}.",
            hint="Confira o .env ou as variáveis OPTIMUS_* (veja .env.example).",
        ) from exc

    rows = {
        "Versão": __version__,
        "Projeto": str(state.workspace),
        "Provider principal": f"{settings.primary_provider} ({settings.primary_model})",
        "Provider secundário": str(settings.secondary_provider or "nenhum"),
    }
    for provider in ProviderName:
        rows[f"Chave {provider.value}"] = (
            "configurada" if settings.has_key_for(provider) else "ausente"
        )
    rows["Nível de log"] = settings.log_level.value
    state.presenter.key_values("Optimus Cyber — status", rows)
