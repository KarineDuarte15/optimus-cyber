"""Logs estruturados em JSON com redação de segredos.

Logs nunca vão para stdout (que é a saída do usuário). Sem arquivo
configurado, só aparecem em stderr no modo ``--debug``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from optimus_cyber.security.redaction import SecretRedactor

ROOT_LOGGER = "optimus_cyber"
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message"}


def get_logger(name: str) -> logging.Logger:
    """Logger filho do logger raiz do Optimus."""
    return logging.getLogger(f"{ROOT_LOGGER}.{name}")


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """Registra um evento com campos estruturados."""
    logger.log(level, event, extra={"event": event, **fields})


class RedactingFilter(logging.Filter):
    """Redige segredos na mensagem e em todos os campos extras."""

    def __init__(self, redactor: SecretRedactor) -> None:
        super().__init__()
        self._redactor = redactor

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redactor.redact(record.getMessage())
        record.args = None
        for key, value in list(record.__dict__.items()):
            if key not in _RESERVED:
                record.__dict__[key] = self._clean(value)
        return True

    def _clean(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._redactor.redact(value)
        if isinstance(value, Mapping):
            return {k: self._clean(v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return [self._clean(v) for v in value]
        return value


class JsonFormatter(logging.Formatter):
    """Uma linha JSON por registro."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(
    *,
    level: str,
    redactor: SecretRedactor,
    log_file: Path | None = None,
    debug: bool = False,
) -> logging.Logger:
    """Configura o logger raiz do Optimus (idempotente)."""
    root = logging.getLogger(ROOT_LOGGER)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    root.propagate = False
    root.setLevel(logging.DEBUG if debug else level)

    handlers: list[logging.Handler] = []
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    if debug:
        handlers.append(logging.StreamHandler())  # stderr
    if not handlers:
        handlers.append(logging.NullHandler())

    for handler in handlers:
        handler.addFilter(RedactingFilter(redactor))
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    return root
