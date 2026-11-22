"""Fábrica de providers e a API de alto nível generate()."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

from fakes.providers import FakeProvider, make_response
from optimus_cyber.config.settings import AppSettings, ProviderName
from optimus_cyber.core.errors import ConfigError
from optimus_cyber.core.models import Message, Role
from optimus_cyber.llm import LLMService, generate
from optimus_cyber.llm import factory as factory_module
from optimus_cyber.llm.claude import ClaudeProvider
from optimus_cyber.llm.config import ProviderConfig
from optimus_cyber.llm.factory import create_provider, register_provider, registered_providers
from optimus_cyber.llm.gemini import GeminiProvider
from optimus_cyber.llm.retry import RetryingProvider

GEMINI_KEY = "AIza" + "G" * 35
CLAUDE_KEY = "sk-ant-api03-" + "c" * 30


@pytest.fixture
def restore_registry() -> Iterator[None]:
    saved = dict(factory_module._REGISTRY)
    yield
    factory_module._REGISTRY.clear()
    factory_module._REGISTRY.update(saved)


def _settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> AppSettings:
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return AppSettings()


def test_missing_key_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigError) as exc:
        create_provider(_settings(monkeypatch))
    assert exc.value.hint is not None
    assert "GEMINI_API_KEY" in exc.value.hint


def test_blank_key_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigError):
        create_provider(_settings(monkeypatch, GEMINI_API_KEY="   "))


def test_creates_gemini_with_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, GEMINI_API_KEY=GEMINI_KEY, OPTIMUS_MAX_RETRIES="2")
    provider = create_provider(settings)
    assert isinstance(provider, RetryingProvider)
    assert isinstance(provider.inner, GeminiProvider)
    assert provider.model == "gemini-2.5-pro"


def test_provider_env_switches_to_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, OPTIMUS_PROVIDER="claude", ANTHROPIC_API_KEY=CLAUDE_KEY)
    provider = create_provider(settings)
    assert isinstance(provider, RetryingProvider)
    assert isinstance(provider.inner, ClaudeProvider)
    assert provider.model == "claude-sonnet-5-5"


def test_model_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, GEMINI_API_KEY=GEMINI_KEY, OPTIMUS_MODEL="gemini-2.5-flash")
    assert create_provider(settings).model == "gemini-2.5-flash"


def test_explicit_provider_overrides_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, ANTHROPIC_API_KEY=CLAUDE_KEY)
    assert create_provider(settings, ProviderName.CLAUDE).name == "claude"


@pytest.mark.usefixtures("restore_registry")
def test_new_provider_can_be_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[ProviderConfig] = []

    def builder(config: ProviderConfig) -> FakeProvider:
        received.append(config)
        return FakeProvider()

    register_provider(ProviderName.GEMINI, builder)
    provider = create_provider(_settings(monkeypatch, GEMINI_API_KEY=GEMINI_KEY))
    assert provider.name == "fake"
    assert received[0].api_key.get_secret_value() == GEMINI_KEY
    assert GEMINI_KEY not in repr(received[0])


@pytest.mark.usefixtures("restore_registry")
def test_unregistered_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    factory_module._REGISTRY.pop(ProviderName.CLAUDE)
    assert ProviderName.CLAUDE not in registered_providers()
    with pytest.raises(ConfigError):
        create_provider(_settings(monkeypatch, ANTHROPIC_API_KEY=CLAUDE_KEY), ProviderName.CLAUDE)


# ------------------------------------------------------------------ service
def test_generate_from_text_applies_defaults() -> None:
    fake = FakeProvider()
    service = LLMService(fake, temperature=0.4, max_output_tokens=256)
    response = asyncio.run(service.generate("pergunta", system="regras"))
    request = fake.requests[0]
    assert response.content == "resposta falsa"
    assert [m.role for m in request.messages] == [Role.SYSTEM, Role.USER]
    assert request.temperature == 0.4
    assert request.max_output_tokens == 256


def test_generate_overrides_defaults() -> None:
    fake = FakeProvider()
    service = LLMService(fake, temperature=0.4, max_output_tokens=256)
    asyncio.run(service.generate("x", temperature=0.0, max_output_tokens=10))
    assert fake.requests[0].temperature == 0.0
    assert fake.requests[0].max_output_tokens == 10


def test_generate_accepts_conversation() -> None:
    fake = FakeProvider()
    conversation = [Message.user("a"), Message.assistant("b"), Message.user("c")]
    asyncio.run(LLMService(fake).generate(conversation))
    assert fake.requests[0].messages == tuple(conversation)
    asyncio.run(LLMService(fake).generate(Message.user("só uma")))
    assert fake.requests[1].messages == (Message.user("só uma"),)


def test_temperature_dropped_when_unsupported() -> None:
    fake = FakeProvider(supports_temperature=False)
    asyncio.run(LLMService(fake, temperature=0.9).generate("x"))
    assert fake.requests[0].temperature is None
    assert LLMService(fake).provider is fake


@pytest.mark.usefixtures("restore_registry")
def test_module_level_generate_uses_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeProvider([make_response("via generate()")])
    register_provider(ProviderName.GEMINI, lambda _config: fake)
    settings = _settings(monkeypatch, GEMINI_API_KEY=GEMINI_KEY, OPTIMUS_TEMPERATURE="0.7")
    response = asyncio.run(generate("oi", system="seja breve", settings=settings))
    assert response.content == "via generate()"
    assert fake.requests[0].temperature == 0.7
    assert fake.requests[0].max_output_tokens == 8192
