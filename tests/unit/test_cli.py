"""Testes da CLI base."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from optimus_cyber import __version__
from optimus_cyber.cli.app import EXIT_CONFIG_ERROR, app

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "status" in result.output


def test_status_without_keys() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "gemini-2.5-pro" in result.output
    assert "ausente" in result.output


def test_status_never_prints_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = "fake-gemini-value-xyz"
    monkeypatch.setenv("GEMINI_API_KEY", sentinel)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "configurada" in result.output
    assert sentinel not in result.output


def test_status_with_invalid_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIMUS_PRIMARY_PROVIDER", "invalido")
    result = runner.invoke(app, ["status"])
    assert result.exit_code == EXIT_CONFIG_ERROR
