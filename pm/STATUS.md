# Project Status

_Last updated: 2026-03-16_

## Current State: Stages 1–3 complete, Stage 5 harness foundation in place

### What's built

**API (Stage 1)**
- `POST /investigate`, `GET /investigations`, `GET /investigations/{id}`
- `GET /reports`, `GET /reports/{id}`
- `GET /runbooks`, `GET /runbooks/{name}`
- `POST /hunt` (501 stub)

**Orchestration (Stage 2)**
- `Orchestrator` → `Router` → `RunbookRegistry` pipeline
- Runbook format: YAML frontmatter + Markdown body in `runbooks/`
- Generic fallback runbook (`runbooks/generic.md`)
- `SQLitePersistence` for investigations

**Agent pipeline (Stage 3)**
- `BaseAgent[TOutput]` — thin PydanticAI wrapper
- `DataAgent` (abstract) → `DataSQLiteAgent` — tools: `list_tables`, `get_schema`, `get_sample`, `run_query`
- `AnalystAgent` — owns `DataSQLiteAgent` internally, exposes `query_data` tool, returns structured `IncidentReport`
- Schema context auto-injected into agent system prompt at init
- Config via `src/config.py` (env-overridable)

**Test harness (Stage 5 foundation)**
- `tests/harness/seeder/synthetic_db.py` — reproducible SQLite dataset with planted brute-force scenario
- `tests/harness/cases/base_case.py` + `case_brute_force.py` — first real e2e case
- `tests/harness/judge.py` — assertion-based evaluator (LLM-as-judge stub)
- `tests/harness/main.py` — CLI runner (`make harness`)
- `tests/harness/seeder/scalyr_db.py` — stub for future real dataset

**Test suite**
- `tests/unittests/` — API routes + schema validation (no LLM)
- `tests/integration/db/` — DataSQLiteAgent against seeded DB (no LLM)
- CI: GitHub Actions for unit + integration on every push

### What's NOT built yet

- Stage 4: EnrichmentAgent (VirusTotal, web lookup, IDP)
- Stage 5 completion: LLM-as-judge scoring, multi-model benchmarking, real golden datasets
- Clickhouse backend (DataClickhouseAgent) — data backend is hardcoded to SQLite today
- ThreatHunterAgent + MCP server
- ReviewerAgent, DetectionEngineerAgent
- Docker container

### Key files for orientation

| Purpose | File |
|---------|------|
| Architecture spec | `pm/DESIGN.md` |
| Agent design + flows | `pm/AGENT_DESIGN.md` |
| Roadmap | `pm/MILESTONES.md` |
| Open questions | `pm/TODO.md` |
| Project instructions | `CLAUDE.md` |
| Entry point | `main.py` |
| Config | `src/config.py` |
| Agent pipeline | `src/agents/` |
| Harness | `tests/harness/` |

### Next up

1. **Real dataset for harness** — source a licensed auth log dataset, implement `ScalyrDataset` or similar loader
2. **Dynamic backend selection** — replace hardcoded SQLite in `AnalystAgent` with configurable backend (`DataAgent.create()`)
3. **EnrichmentAgent** (Stage 4)
