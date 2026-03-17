# Benny, never sleeps, Watchman.

Benny is an autonomous AI security analyst. He receives alerts via REST API, investigates them using an agentic reasoning loop against your log data, and returns structured triage reports — fully unattended, 24/7.

*Benny's on it.*

## How it works

1. An alert arrives via `POST /investigate`
2. The **Orchestrator** matches the alert type to a **Runbook** (YAML + Markdown investigation instructions)
3. The **AnalystAgent** runs a ReAct loop — querying log data and reasoning until it reaches a conclusion or hits the iteration limit
4. A structured **Incident Report** is returned and persisted

## Stack

- **Python 3.14** — Flask API, PydanticAI agents
- **PydanticAI** — multi-agent framework with model-agnostic LLM support
- **Pluggable data backends** — SQLite now; ClickHouse, Elasticsearch, and others via subclassed `DataAgent`
- **SQLite** — local persistence (pluggable; swap for any backend via config)
- **Logfire** — observability for agent runs, tool calls, and token usage
- **Docker** — immutable runtime; runbook changes trigger a new build

## Agents

| Agent | Role |
|---|---|
| `AnalystAgent` | Core investigation loop — drives the ReAct cycle |
| `DataAgent` | Translates data requests into backend queries (Clickhouse, Elasticsearch, …) |
| `EnrichmentAgent` | Enriches IPs, domains, hashes via threat intel APIs |
| `ReviewerAgent` | Critically re-examines findings before finalising the report *(post-MVP)* |
| `DetectionEngineerAgent` | Drafts detection rule improvements for false positives *(post-MVP)* |
| `ThreatHunterAgent` | Interactive ad-hoc hunting via MCP client session *(post-MVP)* |

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/investigate` | Submit an alert, returns an `Investigation` |
| `GET` | `/investigations` | List all investigations |
| `GET` | `/investigations/{id}` | Get investigation by id |
| `GET` | `/reports` | List completed incident reports |
| `GET` | `/reports/{id}` | Get report by investigation id |
| `GET` | `/runbooks` | List available runbooks |
| `GET` | `/runbooks/{name}` | Get runbook by name |
| `POST` | `/hunt` | Interactive threat hunt *(not implemented)* |

## Getting started

```bash
# Install dependencies
make install

# Run the API
make run

# Run tests
make test
```

## Configuration

All settings are read from environment variables:

| Variable | Default | Description |
|---|---|---|
| `AGENT_MODEL` | `google-gla:gemini-3.1-flash-lite-preview` | LLM to use for all agents |
| `AGENT_MODEL_API_KEY` | — | API key — mapped to the correct provider env var automatically |
| `AGENT_MAX_REQUESTS` | `15` | Hard cap on LLM requests per agent run |
| `AGENT_MAX_DATA_REQUESTS` | `10` | Hard cap on LLM requests for DataAgent runs |
| `DATA_BACKEND_ENGINE` | `sqlite` | Data backend (`sqlite`, …) |
| `DATA_BACKEND_DB_PATH` | `data.db` | Path to the security log database |
| `PERSISTENCE_ENGINE` | `sqlite` | Investigation storage backend |
| `PERSISTENCE_DB_PATH` | `investigations.db` | Path to the investigations database |
| `RUNBOOKS_PATH` | `runbooks` | Directory containing runbook `.md` files |

## Runbooks

Runbooks live in `runbooks/` as Markdown files with YAML frontmatter:

```markdown
---
name: brute-force
description: Investigate repeated failed authentication attempts
---

## Instructions
...investigation steps...
```

The alert's `type` field is matched against runbook names. Falls back to `generic` if no match is found.

## Development

```bash
make lint              # ruff check + format check
make fmt               # auto-format
make test-unit         # unit tests only
make test-integration  # API + integration tests
make seed-db           # seed data.db with synthetic security logs
make harness           # run golden-test harness against a live LLM
```
