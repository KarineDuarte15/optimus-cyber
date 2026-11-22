"""Camada de LLM: interface única, adaptadores, retry e a função ``generate()``.

Os SDKs (google-genai, anthropic) só são importados dentro dos adaptadores,
e só quando um provider é criado.
"""

from optimus_cyber.llm.config import ProviderConfig
from optimus_cyber.llm.factory import create_provider, register_provider
from optimus_cyber.llm.service import LLMService, generate

__all__ = ["LLMService", "ProviderConfig", "create_provider", "generate", "register_provider"]
