# Optimus Cyber

Agente de engenharia de software executado no terminal. Ele diagnostica erros, explica stacktraces,
propõe correções e automatiza tarefas de desenvolvimento, sempre por meio de ferramentas controladas
e com aprovação humana para ações de risco.

> **Status:** Etapa 04 — LLM. `optimus ask` já consulta o Gemini (ou o Claude). Os demais
> comandos validam a entrada e mostram o plano; a execução pelos agentes vem nas próximas etapas.

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

Preencha a chave do provider escolhido. O `.env` está no `.gitignore` e nunca deve ser
versionado. Variáveis do sistema têm prioridade sobre o `.env`.

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `GEMINI_API_KEY` | — | Chave do Gemini |
| `ANTHROPIC_API_KEY` | — | Chave do Claude |
| `OPTIMUS_PROVIDER` | `gemini` | `gemini` ou `claude` |
| `OPTIMUS_MODEL` | padrão do provider | `gemini-2.5-pro` / `claude-sonnet-5-5` |
| `OPTIMUS_TEMPERATURE` | `0.2` | 0 a 2 (o Claude atual não aceita e ignora) |
| `OPTIMUS_MAX_OUTPUT_TOKENS` | `8192` | Limite da resposta (no Gemini 2.5 inclui o raciocínio) |
| `OPTIMUS_REQUEST_TIMEOUT_SECONDS` | `120` | Timeout por chamada |
| `OPTIMUS_MAX_RETRIES` | `3` | Tentativas extras em falhas temporárias (429, 5xx, rede) |
| `OPTIMUS_RETRY_BASE_DELAY_SECONDS` | `1` | Base do backoff exponencial |
| `OPTIMUS_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `OPTIMUS_LOG_FILE` | — | Arquivo de log JSON; sem ele, logs só com `--debug` |

Os logs nunca incluem chaves nem o conteúdo de perguntas e respostas: registram provider,
modelo, tokens, latência e erros, sempre passando por redação de segredos.

## Uso da camada de LLM no código

```python
from optimus_cyber.llm import generate

response = await generate("Explique: KeyError 'user_id'", system="Seja breve.")
print(response.content, response.usage.total, response.finish_reason)
```

O restante da aplicação conhece só `LLMProvider` e `LLMResponse`; os SDKs ficam isolados em
`llm/gemini.py` e `llm/claude.py`. Um provider novo é registrado com `register_provider`.

## Uso

| Comando | O que faz |
| --- | --- |
| `optimus ask "pergunta"` | Pergunta ao modelo (ainda sem ler o projeto) |
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
| 3 | Configuração inválida ou chave ausente |
| 4 | Erro do provider de LLM (chave recusada, cota, indisponível) |
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

Testes que chamam APIs reais usam o marcador `live` e ficam desligados por padrão. Com a
chave no `.env`: `python -m pytest -m live --no-cov` (sem chave, eles são pulados).

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
