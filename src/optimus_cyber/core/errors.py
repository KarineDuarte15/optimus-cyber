"""Hierarquia de exceções do Optimus Cyber.

Falhas de infraestrutura e de uso sobem como exceções tipadas; a CLI as
converte em mensagem amigável e exit code. Novas classes (providers, tools,
permissões) entram nas etapas correspondentes.
"""

from __future__ import annotations

from typing import ClassVar


class OptimusError(Exception):
    """Base de todas as exceções do Optimus Cyber."""

    exit_code: ClassVar[int] = 1

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class InputError(OptimusError):
    """Entrada do usuário inválida após o parsing dos argumentos."""

    exit_code: ClassVar[int] = 2


class ConfigError(OptimusError):
    """Configuração ausente ou inválida."""

    exit_code: ClassVar[int] = 3
