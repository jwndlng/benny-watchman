<p align="center">
  <img src="logo.jpeg" alt="Benny Watchman logo">
</p>

# Benny, never sleeps, Watchman.

[![Unit Tests](https://github.com/jwndlng/benny-watchman/actions/workflows/test.yml/badge.svg)](https://github.com/jwndlng/benny-watchman/actions/workflows/test.yml)
[![Integration Tests](https://github.com/jwndlng/benny-watchman/actions/workflows/integration-test.yml/badge.svg)](https://github.com/jwndlng/benny-watchman/actions/workflows/integration-test.yml)
[![Lint](https://github.com/jwndlng/benny-watchman/actions/workflows/lint.yml/badge.svg)](https://github.com/jwndlng/benny-watchman/actions/workflows/lint.yml)

Benny is an autonomous AI security analyst — a small **team of domain experts** you can hand work to. He receives alerts and vulnerability findings via REST API, investigates them with agentic reasoning loops against your data, and returns structured triage reports — fully unattended, 24/7.

*Benny's on it.*

## How it works

1. A request arrives — a security alert (`POST /investigate`) or a vulnerability finding (`POST /findings`).
2. The **OrchestratorAgent** routes it to the right **module** (SIEM or Vulnerability Management). Each request is investigated **once** — a repeat submission returns the stored result (`200`) instead of re-running.
3. The module matches a **Runbook** (YAML + Markdown playbook) and runs its analyst — a ReAct loop that queries data and reasons until it reaches a verdict or hits the iteration limit.
4. A structured report is persisted inside a domain-agnostic **Investigation** envelope (with a generic `outcome` for cross-domain listing).

## Architecture

Benny is organized along a **horizontal / vertical** seam so new triage domains drop in as modules without touching the core:

- **Modules (verticals)** — one per triage domain; each owns its input, playbooks, analyst, and report:
  - **SIEM** — triages security alerts (`Alert` → `IncidentReport`)
  - **Vulnerability Management** — triages scanner findings (`Finding` → `VulnTriageReport`)
- **Capabilities (horizontals)** — shared by every module:
  - **Data** — natural-language queries against a backend (SQLite / Elasticsearch / …)
  - **Identity** — user, role, and access context (Okta)
  - **Enrichment** *(planned)* — threat intel for indicators / CVEs
- **Core** — `BaseAgent` framework, `OrchestratorAgent` (routing + idempotency), `ModuleRegistry`, and the `Capabilities` container.
- **Adapters** — the outer I/O ring: the REST API and MCP server (inbound), plus the systems Benny works *within* — **Platforms** (`TriagePlatform`: supply alerts, receive comment/disposition/case/status; a triage-loop pulls open alerts → investigates → writes back, case-always / auto-close benign / escalate real; in-memory dev impl + `ElasticSecurityPlatform` over the Kibana API; triggered by `POST /triage/run`), query **engines**, and persistence.

Adding a triage domain = adding a `src/modules/<domain>/` folder that implements the `AnalystModule` contract. The layout makes the layering explicit: `src/core/` (framework), `src/capabilities/{subagents,tools}/` (shared skills), `src/modules/` (self-contained verticals), and `src/adapters/{api,mcp,platforms,engines}/` (the I/O ring). Dependencies point inward.

## Components

| Component | Kind | Role |
|---|---|---|
| `OrchestratorAgent` | core | Routes each request to a module; enforces review-once |
| SIEM module | vertical | Triages alerts → verdict + SOC actions |
| Vulnerability Management module | vertical | Triages findings → exploitability, priority, remediation SLA |
| `DataAgent` | capability | Translates NL data requests into backend queries (SQLite, Elasticsearch, …) |
| `IdentityCapability` | capability | User / employment / access context (Okta) |
| Enrichment | capability | Enriches IPs, domains, hashes, CVEs via threat intel |

*Planned:* conversational MCP (`query`/`recall` through the orchestrator, incl. threat hunting), cross-module "lead-analyst" synthesis, detection-rule drafting.

## Stack

- **Python 3.14** — FastAPI application, PydanticAI agents
- **PydanticAI** — model-agnostic multi-agent framework (Anthropic, Google, OpenAI)
- **Pluggable data backends** — SQLite (dev) and Elasticsearch today; ClickHouse next, via a `QueryEngine` implementation
- **SQLite** — investigation persistence (pluggable via config)
- **Logfire** — observability for agent runs, tool calls, and token usage
- **Docker** — immutable runtime; repo changes (runbooks, config) trigger a new build

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/investigate` | Submit a security alert → `Investigation` (`202` fresh / `200` deduped) |
| `POST` | `/findings` | Submit a vulnerability finding → `Investigation` (`202` / `200`) |
| `GET` | `/investigations` | List all investigations |
| `GET` | `/investigations/{id}` | Get investigation by id |
| `GET` | `/reports` | List completed reports |
| `GET` | `/reports/{id}` | Get report by investigation id |
| `GET` | `/runbooks` | List available runbooks |
| `GET` | `/runbooks/{name}` | Get runbook by name |
| `POST` | `/triage/run` | Run one triage-loop pass over the configured platform (pull → investigate → write-back) |
| `POST` | `/hunt` | Interactive threat hunt *(not yet implemented)* |

## MCP server

Benny exposes a Streamable HTTP MCP server at `/mcp` alongside the REST API, so LLM clients can use it directly. Tools: `list_runbooks`, `lookup_data`, `check_platform_access` (read-only triage-platform connectivity/privilege check), and `review_newest_alert` (triage the single newest open alert on demand). On first run a bearer token is printed to stdout unless `MCP_BEARER_TOKEN` is set. See `AGENT.md` for client configuration.

## Getting started

```bash
make install      # install dependencies
make seed-db      # seed data.db with synthetic security logs (SIEM)
make run          # run the API
make test         # run the test suite
```

Seed the dev asset inventory for the Vulnerability Management module:

```bash
uv run python tests/harness/seeder/asset_db.py --db-path vuln.db --reset
```

## Configuration

All settings are read from environment variables:

| Variable | Default | Description |
|---|---|---|
| `AGENT_MODEL` | `google-gla:gemini-3.1-flash-lite-preview` | LLM used by all agents |
| `AGENT_MODEL_API_KEY` | — | API key — mapped to the correct provider env var automatically |
| `AGENT_MAX_REQUESTS` | `15` | Hard cap on LLM requests per agent run |
| `AGENT_MAX_DATA_REQUESTS` | `10` | Hard cap on LLM requests for DataAgent runs |
| `DATA_BACKEND_DB_PATH` | `data.db` | SIEM log database |
| `DATA_AGENT_NAME` | `security_logs` | Name of the SIEM data source |
| `VULN_DB_PATH` | `vuln.db` | VM asset/vulnerability inventory database |
| `VULN_RUNBOOKS_PATH` | `src/modules/vuln_mgmt/runbooks` | VM runbook directory |
| `RUNBOOKS_PATH` | `src/modules/siem/runbooks` | SIEM runbook directory |
| `PERSISTENCE_DB_PATH` | `investigations.db` | Investigation storage |
| `MCP_BEARER_TOKEN` | *(generated)* | Bearer token for the MCP server |
| `LOG_LEVEL` | `INFO` | Root log level; `DEBUG` also unmutes httpx/elasticsearch per-request logs |
| `LOG_FORMAT` | `console` | `console` (colored, human-readable) or `json` (one object per line, for log collectors) |

All subsystems (uvicorn, MCP, HTTP clients, Benny's own logs) render through a single [structlog](https://www.structlog.org) pipeline — colored in a terminal, structured JSON in production.

Optional integrations (auto-disabled when unset): `ELASTIC_HOST` / `ELASTIC_API_KEY` / `ELASTIC_INDEX_PATTERN` (Elasticsearch data source), `KIBANA_URL` / `KIBANA_TRIAGE_API_KEY` / `KIBANA_CASE_OWNER` (the Elastic triage platform — API key scoped to alerts-read + signal-status-write + cases, never remediation), `OKTA_DOMAIN` / `OKTA_CLIENT_ID` / `OKTA_PRIVATE_KEY` (identity capability), `LOGFIRE_TOKEN` (Logfire tracing).

## Runbooks

Runbooks are Markdown files with YAML frontmatter, owned by each module:
`src/modules/siem/runbooks/` (SIEM) and `src/modules/vuln_mgmt/runbooks/` (VM).

```markdown
---
name: brute-force
description: Investigate repeated failed authentication attempts
---
...investigation steps...
```

The input's `type` field is matched against runbook names, falling back to `generic` if no match is found.

## Development

```bash
make lint              # ruff check + format check
make fmt               # auto-format
make test-unit         # unit tests only
make test-integration  # API + integration tests
make harness           # run golden-test harness against a live LLM
```
