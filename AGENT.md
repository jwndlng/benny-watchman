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

## Agent boundaries & cost (the compression-boundary rule)

Benny is built from two kinds of agents: **vertical analyst modules** (SIEM, later VM) that own a triage domain end-to-end, over shared **horizontal capabilities** (data, identity, enrichment) under an `OrchestratorAgent`. Every agentic loop re-sends its whole history each turn, so context cost grows ~quadratically with tool-call turns. Put a boundary wherever multiple round-trips would otherwise pile up in a parent's expensive context — but decide *what kind* of boundary with this rule:

| Unit of work | Compresses parent context? | Needs reasoning? | Build as |
|---|---|---|---|
| Single call | no | no | inline tool |
| N fixed calls, fixed summary | **yes** | no | **composite deterministic tool** (e.g. `IdentityCapability`) |
| N calls, path/verdict decided by a model | **yes** | yes | **sub-agent (LLM loop)** (e.g. `DataAgent`) |
| The investigation's own top-level reasoning | n/a | yes | the analyst itself — **never sharded** |

Two guardrails: **"needs reasoning" ≠ "has a parameter"** (a parameterized-but-fixed query is still a composite tool); and **don't shard the core reasoning** (the "what's the verdict?" step is the analyst's job). Reserve LLM loops for genuine planning or a high raw→distilled ratio; make everything else a plain/composite tool. This keeps the agent tree from quietly becoming an expensive N-deep nest.

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

## MCP Server

Benny exposes a Streamable HTTP MCP server at `/mcp` alongside the REST API. Start the app normally and register it in your Claude Code settings.

**`.claude/settings.json`:**
```json
{
  "mcpServers": {
    "benny": {
      "url": "http://localhost:5000/mcp/",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

Alternatively register it in any other LLM agent such as Antigravity CLI (`~/.gemini/config/mcp_config.json`):

```json
{
  "mcpServers": {
    "benny": {
      "serverUrl": "http://localhost:5000/mcp/",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

**Token:** on first run, a token is printed to stdout if `MCP_BEARER_TOKEN` is not set. Copy it to `.env` as `MCP_BEARER_TOKEN=<token>` to make it stable across restarts.

**Available tools:**
- `list_runbooks` — discover what alert types Benny can investigate
- `lookup_data` — natural-language query against configured data sources

## Project Structure

Source is organized along a horizontal/vertical seam (see `openspec/changes/modular-soc-architecture`):
- `src/core/` — domain-agnostic framework and orchestration (`core/agents/base_agent.py`, `core/orchestration/`)
- `src/capabilities/` — cross-cutting horizontals shared by all domains: `data/` (DataAgents), `identity/` (Okta), `enrichment/`
- `src/modules/` — per-domain verticals; `modules/siem/` holds the SIEM analyst, detection engineer, `Alert`/`IncidentReport` schemas, and `runbooks/`
- `src/mcp/server/` — Benny AS an MCP server (FastMCP assembly, tools, auth); `src/mcp/clients/` — Benny AS a client of external MCP servers (e.g. ClickHouse)
- `src/engines/`, `src/config.py`, `src/models.py`, `src/utils/` — shared infrastructure

### Orchestration & the module contract
- A triage domain is an `AnalystModule` (`src/core/orchestration/module.py`): a Protocol with `name`, `input_type`, `accepts(raw)`, and `investigate(inp, caps)`. Adding a domain means adding a module — not modifying core.
- `OrchestratorAgent` (`src/core/orchestration/orchestrator.py`) exposes `handle(raw, hint=None)`: an explicit `hint` dispatches directly (no LLM); otherwise it resolves a module via `accepts()`. Routes to one module today; the return type leaves room for cross-module synthesis.
- `ModuleRegistry` holds modules (domain-level); `RunbookRegistry` selects playbooks *within* a module — two registries at two levels.
- `Capabilities` (`src/core/orchestration/capabilities.py`) is a typed container of shared instances (data agents, identity), built once at the composition root (`api/app.py`) and injected into `investigate()`. `SIEMModule` (`src/modules/siem/module.py`) is the first module.

## Key Files
- `src/modules/siem/runbooks/` — SIEM runbook definitions (YAML frontmatter + Markdown)
- `src/engines/` — Query engine abstractions (SQLite now, ClickHouse next)
- `src/core/agents/base_agent.py` — BaseAgent framework
- `src/modules/siem/analyst.py` — SIEM AnalystAgent; `src/capabilities/data/` — DataAgents
- `src/models.py` — Persistence models backed by Engine
- `src/core/orchestration/runbook_registry.py` — Runbook loader and matcher
