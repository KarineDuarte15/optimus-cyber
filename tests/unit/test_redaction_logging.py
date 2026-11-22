"""Redação de segredos e logs JSON."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from optimus_cyber.observability.logging import (
    ROOT_LOGGER,
    configure_logging,
    get_logger,
    log_event,
)
from optimus_cyber.security.redaction import REDACTED, SecretRedactor

GOOGLE_KEY = "AIza" + "B" * 35
ANTHROPIC_KEY = "sk-ant-api03-" + "x" * 30


@pytest.mark.parametrize(
    "text",
    [
        f"key={GOOGLE_KEY}",
        f"usando {ANTHROPIC_KEY} agora",
        "Authorization: Bearer abc.def.ghi123456",
        "GEMINI_API_KEY=qualquer-valor-123",
        'password: "hunter2hunter2"',
        "token=ghp_" + "a" * 30,
    ],
)
def test_patterns_are_redacted(text: str) -> None:
    redacted = SecretRedactor().redact(text)
    assert REDACTED in redacted
    for secret in (
        GOOGLE_KEY,
        ANTHROPIC_KEY,
        "abc.def.ghi123456",
        "qualquer-valor-123",
        "hunter2hunter2",
    ):
        assert secret not in redacted


def test_known_secret_is_redacted_anywhere() -> None:
    redactor = SecretRedactor(["valor-muito-secreto"])
    assert redactor.redact("x valor-muito-secreto y") == f"x {REDACTED} y"


def test_short_values_are_not_registered() -> None:
    assert SecretRedactor(["abc"]).redact("abc") == "abc"


def test_plain_text_is_untouched() -> None:
    text = "KeyError: 'user_id' em app/main.py linha 42"
    assert SecretRedactor().redact(text) == text


def _read_lines(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_json_file_logging_redacts_message_and_fields(tmp_path: Path) -> None:
    log_file = tmp_path / "logs" / "optimus.log"
    configure_logging(level="INFO", redactor=SecretRedactor(["segredo-123456"]), log_file=log_file)
    log_event(
        get_logger("teste"),
        logging.INFO,
        "evento",
        detalhe="contém segredo-123456",
        lista=["segredo-123456"],
        mapa={"k": "segredo-123456"},
    )
    try:
        raise ValueError("falhou com segredo-123456")
    except ValueError:
        get_logger("teste").exception("erro")
    text = log_file.read_text(encoding="utf-8")
    assert "segredo-123456" not in text.split('"exception"')[0]
    entries = _read_lines(log_file)
    assert entries[0]["event"] == "evento"
    assert entries[0]["detalhe"] == f"contém {REDACTED}"
    assert entries[0]["level"] == "INFO"


def test_level_filters_debug(tmp_path: Path) -> None:
    log_file = tmp_path / "o.log"
    configure_logging(level="INFO", redactor=SecretRedactor(), log_file=log_file)
    log_event(get_logger("x"), logging.DEBUG, "invisivel")
    assert not log_file.exists() or "invisivel" not in log_file.read_text(encoding="utf-8")


def test_configure_is_idempotent_and_silent_by_default() -> None:
    configure_logging(level="INFO", redactor=SecretRedactor())
    configure_logging(level="INFO", redactor=SecretRedactor())
    handlers = logging.getLogger(ROOT_LOGGER).handlers
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.NullHandler)


def test_debug_logs_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="INFO", redactor=SecretRedactor(), debug=True)
    log_event(get_logger("x"), logging.DEBUG, "visivel")
    captured = capsys.readouterr()
    assert "visivel" in captured.err
    assert captured.out == ""
    configure_logging(level="INFO", redactor=SecretRedactor())
