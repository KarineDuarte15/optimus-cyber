"""Testes da configuração por ambiente."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from optimus_cyber.config.settings import (
    AppSettings,
    LogLevel,
    ProviderName,
    get_settings,
    load_settings,
)
from optimus_cyber.core.errors import ConfigError

FAKE_KEY = "fake-key-123-nao-real"


def test_defaults() -> None:
    settings = AppSettings()
    assert settings.primary_provider is ProviderName.GEMINI
    assert settings.secondary_provider is ProviderName.CLAUDE
    assert settings.primary_model is None
    assert settings.model_for(ProviderName.GEMINI) == "gemini-2.5-pro"
    assert settings.model_for(ProviderName.CLAUDE) == "claude-sonnet-5-5"
    assert settings.log_level is LogLevel.INFO
    assert settings.gemini_api_key is None


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIMUS_PRIMARY_PROVIDER", "claude")
    monkeypatch.setenv("OPTIMUS_LOG_LEVEL", "DEBUG")
    settings = AppSettings()
    assert settings.primary_provider is ProviderName.CLAUDE
    assert settings.log_level is LogLevel.DEBUG


def test_reads_dotenv_file(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(f"GEMINI_API_KEY={FAKE_KEY}\n", encoding="utf-8")
    settings = AppSettings()
    assert settings.has_key_for(ProviderName.GEMINI)
    assert not settings.has_key_for(ProviderName.CLAUDE)


def test_secret_is_not_exposed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    settings = AppSettings()
    assert FAKE_KEY not in repr(settings)
    assert FAKE_KEY not in str(settings.model_dump())
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == FAKE_KEY


def test_empty_key_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert not AppSettings().has_key_for(ProviderName.CLAUDE)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("OPTIMUS_PRIMARY_PROVIDER", "openai"),
        ("OPTIMUS_LOG_LEVEL", "VERBOSE"),
        ("OPTIMUS_REQUEST_TIMEOUT_SECONDS", "0"),
    ],
)
def test_invalid_values_are_rejected(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        AppSettings()


def test_settings_are_immutable() -> None:
    settings = AppSettings()
    with pytest.raises(ValidationError):
        settings.primary_model = "outro"  # type: ignore[misc]  # violação intencional


def test_short_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIMUS_PROVIDER", "claude")
    monkeypatch.setenv("OPTIMUS_MODEL", "claude-opus-5-5")
    monkeypatch.setenv("OPTIMUS_SECONDARY_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("OPTIMUS_SECONDARY_PROVIDER", "gemini")
    settings = AppSettings()
    assert settings.primary_provider is ProviderName.CLAUDE
    assert settings.model_for(ProviderName.CLAUDE) == "claude-opus-5-5"
    assert settings.model_for(ProviderName.GEMINI) == "gemini-2.5-flash"


def test_dotenv_inline_comments(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "OPTIMUS_TEMPERATURE=0.7          # comentário\n", encoding="utf-8"
    )
    assert AppSettings().temperature == 0.7


def test_load_settings_hides_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIMUS_TEMPERATURE", "valor-estranho-123")
    with pytest.raises(ConfigError) as exc:
        load_settings()
    assert "OPTIMUS_TEMPERATURE" in exc.value.message
    assert "valor-estranho-123" not in exc.value.message


def test_secret_values_lists_configured_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    assert AppSettings().secret_values() == [FAKE_KEY]


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
    get_settings.cache_clear()
