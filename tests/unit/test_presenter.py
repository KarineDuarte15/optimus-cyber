"""Componentes visuais do Presenter, renderizados em console de gravação."""

from __future__ import annotations

from uuid import uuid4

from rich.console import Console

from optimus_cyber.cli.ui.presenter import Presenter
from optimus_cyber.cli.ui.theme import OPTIMUS_THEME
from optimus_cyber.core.models import (
    CommandOutcome,
    Intent,
    OutcomeStatus,
    PlannedStep,
    RiskLevel,
)


def _presenter() -> tuple[Presenter, Console, Console]:
    out = Console(record=True, width=100, theme=OPTIMUS_THEME)
    err = Console(record=True, width=100, theme=OPTIMUS_THEME)
    return Presenter(out, err), out, err


def _outcome(status: OutcomeStatus) -> CommandOutcome:
    return CommandOutcome(
        request_id=uuid4(),
        intent=Intent.FIX,
        status=status,
        summary="corrigir",
        steps=(
            PlannedStep(order=1, agent="Code", description="aplicar", risk=RiskLevel.WRITE),
            PlannedStep(order=2, agent="Git", description="push", risk=RiskLevel.DESTRUCTIVE),
        ),
        notes=("nota",),
    )


def test_header_shows_title_and_mode() -> None:
    presenter, out, _ = _presenter()
    presenter.header("Modo Teste")
    text = out.export_text()
    assert "Terminal Optimus Cyber" in text
    assert "Modo Teste" in text


def test_outcome_shows_risk_labels() -> None:
    presenter, out, _ = _presenter()
    presenter.outcome(_outcome(OutcomeStatus.PREVIEW))
    text = out.export_text()
    assert "escrita" in text
    assert "destrutiva" in text
    assert "nota" in text


def test_failed_outcome_goes_to_stderr() -> None:
    presenter, _, err = _presenter()
    presenter.outcome(_outcome(OutcomeStatus.FAILED))
    assert "falha" in err.export_text()


def test_messages() -> None:
    presenter, out, err = _presenter()
    presenter.info("informação")
    presenter.success("feito")
    presenter.warning("cuidado")
    presenter.error("quebrou", hint="tente isso")
    output = out.export_text()  # export_text() esvazia o buffer
    assert "informação" in output
    assert "feito" in output
    errors = err.export_text()
    assert "cuidado" in errors
    assert "quebrou" in errors
    assert "tente isso" in errors


def test_working_confirms_message() -> None:
    presenter, out, _ = _presenter()
    with presenter.working("processando"):
        pass
    assert "processando" in out.export_text()
