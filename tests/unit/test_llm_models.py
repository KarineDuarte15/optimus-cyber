"""Modelos neutros de LLM."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from optimus_cyber.core.models import FinishReason, LLMRequest, LLMResponse, Message, TokenUsage


def test_request_splits_system_and_conversation() -> None:
    request = LLMRequest(
        messages=(Message.system("regra 1"), Message.system("regra 2"), Message.user("oi"))
    )
    assert request.system_prompt == "regra 1\n\nregra 2"
    assert request.conversation == (Message.user("oi"),)


def test_request_without_system_prompt() -> None:
    assert LLMRequest(messages=(Message.user("oi"),)).system_prompt is None


@pytest.mark.parametrize(
    "messages",
    [
        (),
        (Message.system("só sistema"),),
        (Message.user("oi"), Message.assistant("olá")),
    ],
)
def test_request_rejects_invalid_conversations(messages: tuple[Message, ...]) -> None:
    with pytest.raises(ValidationError):
        LLMRequest(messages=messages)


@pytest.mark.parametrize(
    ("field", "value"), [("temperature", -0.1), ("temperature", 2.1), ("max_output_tokens", 0)]
)
def test_request_rejects_out_of_range(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        LLMRequest.model_validate({"messages": [{"role": "user", "content": "x"}], field: value})


def test_message_cannot_be_empty() -> None:
    with pytest.raises(ValidationError):
        Message.user("")


def test_usage_total_and_truncation() -> None:
    usage = TokenUsage(input_tokens=1, output_tokens=2, reasoning_tokens=3)
    response = LLMResponse(
        content="x", finish_reason=FinishReason.LENGTH, usage=usage, provider="p", model="m"
    )
    assert usage.total == 6
    assert response.truncated
