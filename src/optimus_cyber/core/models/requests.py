"""Requisição do usuário, já normalizada pela CLI."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import Field

from optimus_cyber.core.models.base import DomainModel

OptionValue = str | int | bool | tuple[str, ...] | None


class Intent(StrEnum):
    """Intenção do usuário, uma por comando da CLI."""

    ASK = "ask"
    DIAGNOSE = "diagnose"
    EXPLAIN = "explain"
    FIX = "fix"
    REVIEW = "review"
    TEST = "test"
    COMMIT = "commit"
    DOCS = "docs"
    PROJECT = "project"


class UserRequest(DomainModel):
    """Pedido do usuário independente de interface (CLI hoje, IDE no futuro)."""

    id: UUID = Field(default_factory=uuid4)
    intent: Intent
    workspace: Path
    text: str = ""
    options: dict[str, OptionValue] = Field(default_factory=dict)
