"""Configuração entregue a cada adaptador."""

from __future__ import annotations

from pydantic import Field, SecretStr

from optimus_cyber.core.models.base import DomainModel


class ProviderConfig(DomainModel):
    """Tudo que um adaptador precisa para se conectar."""

    model: str = Field(min_length=1)
    api_key: SecretStr
    timeout_seconds: float = Field(gt=0)
