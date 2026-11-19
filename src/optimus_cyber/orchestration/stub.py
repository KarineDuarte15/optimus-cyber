"""Orquestrador provisório: devolve o plano de cada comando sem executá-lo.

Ele cumpre o mesmo papel que o orquestrador real terá para a CLI
(``await run(request)``), então a CLI não muda quando os agentes chegarem.
Nada aqui chama LLM, lê arquivos ou executa processos.
"""

from __future__ import annotations

from optimus_cyber.core.models import (
    CommandOutcome,
    Intent,
    OutcomeStatus,
    PlannedStep,
    RiskLevel,
    UserRequest,
)

_Step = tuple[str, str, RiskLevel]

_R = RiskLevel.READ_ONLY
_X = RiskLevel.EXECUTE
_W = RiskLevel.WRITE

PLANS: dict[Intent, tuple[str, tuple[_Step, ...]]] = {
    Intent.ASK: (
        "Responder uma pergunta sobre o projeto",
        (
            ("Planner", "Interpretar a pergunta e o contexto do projeto", _R),
            ("Diagnostic", "Localizar arquivos e trechos relevantes", _R),
            ("Planner", "Responder citando os arquivos usados", _R),
        ),
    ),
    Intent.DIAGNOSE: (
        "Diagnosticar um erro a partir de logs ou de um comando",
        (
            ("Diagnostic", "Ler o log ou capturar a saída do comando", _R),
            ("Diagnostic", "Extrair o stacktrace e os frames do projeto", _R),
            ("Diagnostic", "Ler o código em torno das linhas citadas", _R),
            ("Diagnostic", "Identificar a causa provável e sugerir solução", _R),
        ),
    ),
    Intent.EXPLAIN: (
        "Explicar um erro em linguagem técnica clara",
        (
            ("Diagnostic", "Interpretar a mensagem de erro", _R),
            ("Diagnostic", "Relacionar com arquivo, linha e contexto", _R),
            ("Diagnostic", "Apresentar causa e alternativas de solução", _R),
        ),
    ),
    Intent.FIX: (
        "Corrigir um problema com patch controlado",
        (
            ("Diagnostic", "Diagnosticar o problema", _R),
            ("Planner", "Montar o plano de correção", _R),
            ("Code", "Gerar o patch como diff", _R),
            ("Code", "Aplicar o patch após aprovação", _W),
            ("Test", "Executar os testes e validar", _X),
        ),
    ),
    Intent.REVIEW: (
        "Revisar código",
        (
            ("Review", "Ler os arquivos ou o diff selecionado", _R),
            ("Review", "Avaliar qualidade, segurança, desempenho e arquitetura", _R),
            ("Review", "Listar achados por severidade", _R),
        ),
    ),
    Intent.TEST: (
        "Executar e interpretar os testes",
        (
            ("Test", "Detectar o comando de testes do projeto", _R),
            ("Test", "Executar os testes", _X),
            ("Test", "Interpretar falhas e apontar a causa provável", _R),
        ),
    ),
    Intent.COMMIT: (
        "Gerar um commit semântico",
        (
            ("Git", "Ler o status e o diff", _R),
            ("Git", "Propor a mensagem no padrão Conventional Commits", _R),
            ("Git", "Criar o commit após aprovação", _W),
        ),
    ),
    Intent.DOCS: (
        "Atualizar a documentação",
        (
            ("Documentation", "Mapear o que mudou no código", _R),
            ("Documentation", "Propor alterações na documentação como diff", _R),
            ("Documentation", "Aplicar após aprovação", _W),
        ),
    ),
    Intent.PROJECT: (
        "Mapear a arquitetura do projeto",
        (
            ("Planner", "Detectar linguagem, dependências e estrutura", _R),
            ("Planner", "Identificar Docker, CI/CD, banco e serviços", _R),
            ("Planner", "Resumir a arquitetura", _R),
        ),
    ),
}

STUB_NOTE = "Prévia do plano: a execução pelos agentes será implementada nas próximas etapas."


class StubOrchestrator:
    """Implementação provisória do contrato ``run(request) -> CommandOutcome``."""

    async def run(self, request: UserRequest) -> CommandOutcome:
        """Devolve o plano do comando, sem executar nenhuma ação."""
        summary, raw_steps = PLANS[request.intent]
        steps = tuple(
            PlannedStep(order=index, agent=agent, description=description, risk=risk)
            for index, (agent, description, risk) in enumerate(raw_steps, start=1)
        )
        return CommandOutcome(
            request_id=request.id,
            intent=request.intent,
            status=OutcomeStatus.PREVIEW,
            summary=summary,
            steps=steps,
            notes=(STUB_NOTE,),
        )
