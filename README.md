# Optimus Cyber

Agente de engenharia de software executado no terminal. Ele diagnostica erros, explica stacktraces,
propõe correções e automatiza tarefas de desenvolvimento, sempre por meio de ferramentas controladas
e com aprovação humana para ações de risco.

> **Status:** Etapa 03 — CLI. Todos os comandos existem, validam a entrada e mostram o plano
> de execução. A execução real pelos agentes chega nas próximas etapas.

## Requisitos

- Python 3.11 ou superior
- Git
- Chave de API do Gemini (provider principal) e, opcionalmente, do Claude

## Instalação

Com o Python instalado na máquina (sem ambiente virtual):

```bash
python -m pip install -e ".[dev]"
```

Para usar só a CLI, de forma isolada e sem conflitar com outros projetos:

```bash
pipx install .
```

## Configuração

```bash
cp .env.example .env      # PowerShell: Copy-Item .env.example .env
```

Preencha `GEMINI_API_KEY` (e `ANTHROPIC_API_KEY`, se for usar o Claude). O `.env` está no
`.gitignore` e nunca deve ser versionado. Variáveis do sistema têm prioridade sobre o `.env`.

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `GEMINI_API_KEY` | — | Chave do Gemini |
| `ANTHROPIC_API_KEY` | — | Chave do Claude |
| `OPTIMUS_PRIMARY_PROVIDER` | `gemini` | `gemini` ou `claude` |
| `OPTIMUS_PRIMARY_MODEL` | `gemini-2.5-pro` | Modelo do provider principal |
| `OPTIMUS_SECONDARY_PROVIDER` | `claude` | Provider de fallback |
| `OPTIMUS_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `OPTIMUS_REQUEST_TIMEOUT_SECONDS` | `120` | Timeout das chamadas ao LLM |

## Uso

| Comando | O que faz |
| --- | --- |
| `optimus ask "pergunta"` | Pergunta sobre o projeto |
| `optimus doctor [--log ARQ \| --cmd CMD]` | Diagnostica um erro |
| `optimus explain "erro" \| --log ARQ` | Explica um erro |
| `optimus fix --issue TEXTO \| --log ARQ [--dry-run] [--yes]` | Corrige com patch controlado |
| `optimus review [CAMINHOS...] [--focus F] [--staged]` | Revisa código |
| `optimus test [-k FILTRO] [--coverage] [-x]` | Executa e interpreta testes |
| `optimus commit [--type T] [--scope S]` | Gera commit semântico |
| `optimus docs [--target readme\|changelog\|api\|all]` | Atualiza documentação |
| `optimus project [--depth N]` | Explica a arquitetura do projeto |
| `optimus status` | Mostra a configuração, sem revelar segredos |

Opções globais (antes do comando): `--path/-C PASTA`, `--debug`, `--no-color`, `--version/-V`,
`--help/-h`. Exemplo: `optimus -C ../meu-projeto doctor --log logs/app.log`.

| Exit code | Significado |
| --- | --- |
| 0 | Sucesso |
| 1 | Erro inesperado (use `--debug` para detalhes) |
| 2 | Uso incorreto ou entrada inválida |
| 3 | Configuração inválida |
| 130 | Cancelado com Ctrl+C |

No Windows, se o comando `optimus` não for encontrado, adicione a pasta `Scripts` do Python ao
`PATH` ou use `python -m optimus_cyber`.

## Desenvolvimento

```bash
python -m pytest          # testes + cobertura mínima de 80%
python -m ruff check .    # lint
python -m ruff format .   # formatação
python -m mypy            # tipagem estrita
```

Testes que chamam APIs reais usam o marcador `live` e ficam desligados por padrão:
`python -m pytest -m live`.

## Estrutura

```text
src/optimus_cyber/
├── core/           # interfaces abstratas, modelos Pydantic, erros
├── config/         # configuração por ambiente
├── cli/            # Typer + Rich
├── orchestration/  # AI Orchestrator
├── agents/         # agentes especializados
├── tools/          # ferramentas controladas
├── llm/            # providers Gemini e Claude
├── security/       # permissões e redação de segredos
├── memory/         # sessão e persistência
├── validation/     # validadores determinísticos
└── observability/  # logs e auditoria
tests/  docs/  docker/  examples/
```

Veja `docs/architecture.md` para o resumo da arquitetura.

## Segurança

O LLM nunca acessa o sistema diretamente: toda ação passa por ferramentas com schema, permissão,
timeout e auditoria. Chaves de API vêm só de variáveis de ambiente e nunca aparecem em logs ou na
saída da CLI.
