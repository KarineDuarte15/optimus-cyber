"""Remoção de segredos de qualquer texto antes de ser logado ou exibido."""

from __future__ import annotations

import re
from collections.abc import Iterable

REDACTED = "[REDACTED]"
MIN_SECRET_LENGTH = 8

_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),  # chave Google/Gemini
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),  # chave Anthropic
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),  # padrão sk- genérico
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/\-]{8,}=*"),
    re.compile(r"(?i)\b(?:ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}"),
)

_ASSIGNMENT = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:api[_-]?key|token|secret|password|passwd)[A-Z0-9_]*)"
    r"(\s*[:=]\s*)([\"']?)([^\s\"',;&]+)"
)


class SecretRedactor:
    """Substitui segredos conhecidos e padrões de credenciais por ``[REDACTED]``."""

    def __init__(self, known_secrets: Iterable[str] = ()) -> None:
        self._known: set[str] = set()
        for secret in known_secrets:
            self.add(secret)

    def add(self, secret: str) -> None:
        """Registra um valor que nunca pode aparecer (ignora valores curtos)."""
        if len(secret) >= MIN_SECRET_LENGTH:
            self._known.add(secret)

    def redact(self, text: str) -> str:
        """Devolve o texto sem segredos."""
        for secret in sorted(self._known, key=len, reverse=True):
            text = text.replace(secret, REDACTED)
        for pattern in _PATTERNS:
            text = pattern.sub(REDACTED, text)
        return _ASSIGNMENT.sub(lambda m: f"{m[1]}{m[2]}{m[3]}{REDACTED}", text)
