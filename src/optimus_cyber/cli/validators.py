"""Validações de entrada reutilizáveis.

Todas lançam ``typer.BadParameter``, então o Typer mostra a mensagem junto
com o uso correto do comando e sai com código 2.
"""

from __future__ import annotations

import re

import typer

MAX_TEXT_LENGTH = 4000
_SCOPE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,29}$")


def clean_text(value: str | None) -> str | None:
    """Remove espaços nas pontas; rejeita texto vazio ou longo demais."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise typer.BadParameter("não pode ser vazio.")
    if len(stripped) > MAX_TEXT_LENGTH:
        raise typer.BadParameter(f"excede {MAX_TEXT_LENGTH} caracteres.")
    return stripped


def question_text(value: str) -> str:
    """Pergunta obrigatória com pelo menos 3 caracteres."""
    cleaned = clean_text(value) or ""
    if len(cleaned) < 3:
        raise typer.BadParameter("a pergunta precisa ter pelo menos 3 caracteres.")
    return cleaned


def commit_scope(value: str | None) -> str | None:
    """Escopo do Conventional Commits: minúsculas, números, ponto, hífen."""
    if value is None:
        return None
    if not _SCOPE_PATTERN.fullmatch(value):
        raise typer.BadParameter(
            "use letras minúsculas, números, '.', '_' ou '-' (até 30 caracteres)."
        )
    return value


def require_any(**options: object) -> None:
    """Exige que pelo menos uma das opções tenha sido informada."""
    if all(value in (None, False, []) for value in options.values()):
        names = ", ".join(options)
        raise typer.BadParameter(f"informe ao menos um de: {names}.")


def mutually_exclusive(**options: object) -> None:
    """Impede que mais de uma das opções seja usada ao mesmo tempo."""
    used = [name for name, value in options.items() if value not in (None, False, [])]
    if len(used) > 1:
        raise typer.BadParameter(f"use apenas um de: {', '.join(used)}.")
