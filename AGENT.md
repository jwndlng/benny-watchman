# benny-watchman

> Benny, never sleeps, Watchman.

## Project Overview
Benny is an autonomous AI security analyst. He receives alerts via REST API, investigates them using an agentic reasoning loop (ReAct pattern) with SQLite (dev) / ClickHouse (production) log data, and returns structured triage reports. Fully unattended, 24/7 operation.

## Tech Stack
- **Language:** Python
- **API:** Flask
- **Data:** SQLite (dev/test) → ClickHouse via MCP stdio transport (production)
- **LLM:** Model-agnostic (Anthropic, Google, OpenAI) — configurable at runtime via `AGENT_MODEL`
- **Observability:** Logfire (PydanticAI instrumentation + custom spans)
- **Container:** Docker
- **Logging:** Structured JSON to stdout, collected by Vector daemonset

## Key Design Decisions
- Agent is **investigation-only** — it never triggers remediation actions
- Runbooks **scope the investigation** — one runbook per alert type, generic fallback for unmatched
- DB permissions enforced at **ClickHouse user level**, not query parsing
- Web access restricted to a **repo-managed allowlist**
- All repo changes (runbooks, context, allowlist) trigger a **new Docker build**
- Guardrails: `AGENT_MAX_REQUESTS` (hard cap per agent) + per-agent `constraints` (soft guidance)

## Agent Design Principles
- `instructions` defines the agent's persona — pure role description, never overridden by subclasses to append context
- `system_prompt` assembles the final prompt: `instructions + constraints` — defined in `BaseAgent`, not overridden
- `constraints` are agent-specific limits (tool call budgets, query discipline) injected at the end of the system prompt
- Tools are implemented as methods and registered in `__init__` via `self.agent.tool_plain(self.method)` — no closures
- Tool docstrings are the tool description sent to the LLM — keep them precise and include input expectations

## Coding Guidelines
- Use `@property` methods to expose agent behaviour (`instructions`, `system_prompt`, `constraints`) — keeps classes clean and declarative
- Type everything — function signatures, return types, class attributes. Avoid `Any`
- Use Pydantic models or dataclasses for structured data — avoid plain `dict` for anything that crosses a boundary (tool inputs/outputs, API payloads, DB results). Dicts are opaque and make refactoring fragile
- Model fields should have `Field(description=...)` — PydanticAI surfaces these as schema hints to the LLM
- One-line docstrings per method are sufficient — let the code speak for itself. Tools are the exception: use multi-line docstrings when additional guidance is needed to steer the LLM

## Tool Guidelines
- Every tool must have a docstring — this is the description sent to the LLM in the API payload
- Docstrings should describe: what the tool does, what the input expects, and any hard constraints (e.g. SQLite-only, read-only, no `SELECT *`)
- Tools are implemented as methods on the agent class, never as closures
- Tools are registered in `__init__` via `self.agent.tool_plain(self.method)`
- Keep tool results focused and small — every byte returned becomes input tokens on the next LLM turn
- Return structured Pydantic types where possible so the LLM can parse results reliably

## Cost & Performance Observations
- Input tokens dominate cost — context grows with each tool call turn as full history is re-sent
- Schema pre-loaded in system prompt is cheaper than runtime `get_schema` calls when the schema is small and stable
- `SELECT *` constraints on DataAgent cut input tokens significantly (~75% reduction observed)
- Target: 3 `query_data` calls max per investigation (~40k input / 5k output tokens, ~$0.10–0.20)
- DataAgent runs are stateless per `query_data` call — no shared context with AnalystAgent
- Output tokens stay small (final structured JSON + tool calls) — input is the main cost driver

## Key Files
- `runbooks/` — Runbook definitions (YAML frontmatter + Markdown)
- `src/engines/` — Query engine abstractions (SQLite now, ClickHouse next)
- `src/agents/` — AnalystAgent, DataAgent, BaseAgent
- `src/models.py` — Persistence models backed by Engine
- `src/runbook_registry.py` — Runbook loader and matcher
