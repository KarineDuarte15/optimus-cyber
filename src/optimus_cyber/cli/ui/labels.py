"""Textos de modo e de progresso exibidos para cada intenção."""

from optimus_cyber.core.models import Intent

APP_TITLE = "Terminal Optimus Cyber"

MODE_LABELS: dict[Intent, str] = {
    Intent.ASK: "Modo Pergunta",
    Intent.DIAGNOSE: "Modo Diagnóstico",
    Intent.EXPLAIN: "Modo Explicação",
    Intent.FIX: "Modo Correção",
    Intent.REVIEW: "Modo Revisão",
    Intent.TEST: "Modo Testes",
    Intent.COMMIT: "Modo Commit",
    Intent.DOCS: "Modo Documentação",
    Intent.PROJECT: "Modo Projeto",
}

WORKING_LABELS: dict[Intent, str] = {
    Intent.ASK: "Consultando o modelo...",
    Intent.DIAGNOSE: "Analisando o projeto...",
    Intent.EXPLAIN: "Analisando o erro...",
    Intent.FIX: "Preparando o plano de correção...",
    Intent.REVIEW: "Preparando a revisão...",
    Intent.TEST: "Preparando os testes...",
    Intent.COMMIT: "Analisando as alterações...",
    Intent.DOCS: "Analisando a documentação...",
    Intent.PROJECT: "Mapeando o projeto...",
}
