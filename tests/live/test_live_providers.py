"""Chamadas reais. Rodar com: py -m pytest -m live --no-cov

Precisam de chave no ambiente ou no .env da raiz do projeto; sem chave, pulam.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from optimus_cyber.config.settings import AppSettings, ProviderName
from optimus_cyber.llm import LLMService

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.live


@pytest.mark.parametrize("provider", list(ProviderName))
def test_real_generate(provider: ProviderName) -> None:
    settings = AppSettings(_env_file=ROOT / ".env")
    if not settings.has_key_for(provider):
        pytest.skip(f"sem chave para {provider.value}")
    service = LLMService.from_settings(settings, provider)
    response = asyncio.run(service.generate("Responda apenas com a palavra: pong"))
    assert "pong" in response.content.lower()
    assert response.usage.output_tokens > 0
