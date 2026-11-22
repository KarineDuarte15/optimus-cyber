"""Fixtures compartilhadas."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from optimus_cyber.config.settings import get_settings

_KEYS = ("GEMINI_API_KEY", "ANTHROPIC_API_KEY")


@pytest.fixture(autouse=True)
def isolated_env(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Nenhum teste lê variáveis ou .env reais da máquina (exceto os ``live``)."""
    get_settings.cache_clear()
    if request.node.get_closest_marker("live"):
        return
    for name in list(os.environ):
        if name.startswith("OPTIMUS_") or name in _KEYS:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
