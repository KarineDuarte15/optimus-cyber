"""Fixtures compartilhadas."""

from __future__ import annotations

from pathlib import Path

import pytest

_ENV_VARS = (
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPTIMUS_PRIMARY_PROVIDER",
    "OPTIMUS_PRIMARY_MODEL",
    "OPTIMUS_SECONDARY_PROVIDER",
    "OPTIMUS_SECONDARY_MODEL",
    "OPTIMUS_LOG_LEVEL",
    "OPTIMUS_REQUEST_TIMEOUT_SECONDS",
)


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Garante que nenhum teste leia variáveis ou .env reais da máquina."""
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
