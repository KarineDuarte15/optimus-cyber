"""DefaultOrchestrator."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from fakes.providers import FakeProvider
from optimus_cyber.core.errors import ConfigError
from optimus_cyber.core.models import Intent, OutcomeStatus, Role, UserRequest
from optimus_cyber.llm.service import LLMService
from optimus_cyber.orchestration.orchestrator import ASK_SYSTEM_PROMPT, DefaultOrchestrator


def test_ask_calls_llm_with_system_prompt() -> None:
    fake = FakeProvider()
    orchestrator = DefaultOrchestrator(lambda: LLMService(fake))
    request = UserRequest(intent=Intent.ASK, workspace=Path(), text="o que é SOLID?")
    outcome = asyncio.run(orchestrator.run(request))
    assert outcome.status is OutcomeStatus.COMPLETED
    assert outcome.response is not None
    sent = fake.requests[0].messages
    assert sent[0].role is Role.SYSTEM
    assert sent[0].content == ASK_SYSTEM_PROMPT
    assert sent[1].content == "o que é SOLID?"


def test_other_intents_do_not_need_llm() -> None:
    def no_service() -> LLMService:
        raise AssertionError("não deveria criar o serviço")

    orchestrator = DefaultOrchestrator(no_service)
    outcome = asyncio.run(orchestrator.run(UserRequest(intent=Intent.DOCS, workspace=Path())))
    assert outcome.status is OutcomeStatus.PREVIEW


def test_config_errors_propagate() -> None:
    def missing_key() -> LLMService:
        raise ConfigError("sem chave")

    orchestrator = DefaultOrchestrator(missing_key)
    with pytest.raises(ConfigError):
        asyncio.run(orchestrator.run(UserRequest(intent=Intent.ASK, workspace=Path(), text="x")))
