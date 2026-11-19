"""Modelos do core, router e orquestrador stub."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from optimus_cyber.cli.router import CommandRouter
from optimus_cyber.core.models import Intent, OutcomeStatus, PlannedStep, UserRequest
from optimus_cyber.orchestration.stub import PLANS, StubOrchestrator


def test_user_request_is_immutable_and_strict() -> None:
    request = UserRequest(intent=Intent.ASK, workspace=Path())
    with pytest.raises(ValidationError):
        request.text = "outro"  # type: ignore[misc]  # violação intencional
    with pytest.raises(ValidationError):
        UserRequest(intent=Intent.ASK, workspace=Path(), extra="x")  # type: ignore[call-arg]


def test_planned_step_order_starts_at_one() -> None:
    with pytest.raises(ValidationError):
        PlannedStep(order=0, agent="x", description="y")


def test_router_drops_none_options() -> None:
    request = CommandRouter.build(Intent.TEST, Path(), options={"a": None, "b": True})
    assert request.options == {"b": True}


def test_every_intent_has_a_plan() -> None:
    assert set(PLANS) == set(Intent)


@pytest.mark.parametrize("intent", list(Intent))
def test_stub_returns_ordered_preview(intent: Intent) -> None:
    request = UserRequest(intent=intent, workspace=Path())
    outcome = asyncio.run(StubOrchestrator().run(request))
    assert outcome.status is OutcomeStatus.PREVIEW
    assert outcome.request_id == request.id
    assert [step.order for step in outcome.steps] == list(range(1, len(outcome.steps) + 1))
