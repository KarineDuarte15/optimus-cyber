"""Modelo base: imutável e sem campos extras."""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Base para todos os modelos de domínio."""

    model_config = ConfigDict(frozen=True, extra="forbid")
