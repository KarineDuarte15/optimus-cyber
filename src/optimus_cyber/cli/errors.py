"""Tratamento centralizado de erros dos comandos."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import ParamSpec

import typer

from optimus_cyber.cli.state import AppState
from optimus_cyber.cli.ui.presenter import Presenter
from optimus_cyber.core.errors import OptimusError

P = ParamSpec("P")

EXIT_UNEXPECTED = 1
EXIT_INTERRUPTED = 130

# Exceções que o próprio Typer sabe exibir (uso incorreto, saída normal).
_PASSTHROUGH = (typer.Exit, typer.Abort, typer.BadParameter)


def _resolve(ctx: object) -> tuple[Presenter, bool]:
    # O Typer pode entregar o contexto do Click embutido, que não é subclasse
    # de typer.Context; por isso olhamos só o atributo ``obj``.
    state = getattr(ctx, "obj", None)
    if isinstance(state, AppState):
        return state.presenter, state.debug
    return Presenter.create(), False


def handle_errors(func: Callable[P, None]) -> Callable[P, None]:
    """Converte exceções em mensagem Rich e exit code, sem traceback cru.

    O comando decorado deve receber ``ctx: typer.Context``.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        ctx = kwargs.get("ctx", args[0] if args else None)
        try:
            func(*args, **kwargs)
        except _PASSTHROUGH:
            raise
        except OptimusError as exc:
            presenter, _ = _resolve(ctx)
            presenter.error(exc.display_message(), hint=exc.hint)
            raise typer.Exit(code=exc.exit_code) from exc
        except KeyboardInterrupt as exc:
            presenter, _ = _resolve(ctx)
            presenter.warning("Operação cancelada pelo usuário.")
            raise typer.Exit(code=EXIT_INTERRUPTED) from exc
        except Exception as exc:
            presenter, debug = _resolve(ctx)
            presenter.error(
                f"Erro inesperado: {type(exc).__name__}",
                hint="Execute novamente com --debug para ver os detalhes.",
            )
            if debug:
                presenter.exception()
            raise typer.Exit(code=EXIT_UNEXPECTED) from exc

    return wrapper
