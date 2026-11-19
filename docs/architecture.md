# Arquitetura — resumo

Fluxo: Usuário → CLI → Command Router → AI Orchestrator → Planner/Agents → Tools → LLM → Validator → Resposta.

| Módulo | Responsabilidade |
| --- | --- |
| `core` | Interfaces abstratas, modelos Pydantic, erros. Não depende de nada. |
| `config` | Configuração (ambiente, `.env`; `optimus.toml` na Etapa 04). |
| `cli` | Comandos Typer e saída Rich. |
| `orchestration` | Ciclo planejar → executar → observar → validar → explicar. |
| `agents` | Agentes especializados com allowlist de tools. |
| `tools` | Ferramentas controladas e `ToolExecutor`. |
| `llm` | `GeminiProvider`, `ClaudeProvider`, retry e fallback. |
| `security` | Permissões, guarda de caminhos, política de comandos, redação. |
| `memory` | Sessão e armazenamento por projeto (SQLite). |
| `validation` | Validadores determinísticos. |
| `observability` | Logs JSON, auditoria, tracing. |

Princípio central: o LLM nunca acessa o sistema diretamente; ele solicita ações a ferramentas
com schema, permissão, timeout e auditoria.
