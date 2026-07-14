## Why

Benny is a single-domain SIEM alert triage service today, but the vision is a general security analyst — a "SOC engineer" — that gains new triage domains as pluggable modules (SIEM now, Vulnerability Management next, more later) and is reachable both by direct API task ("analyze alert X") and by conversational MCP ("ask Benny about user Y").

The current architecture bakes SIEM assumptions into the core: the `Alert` and `IncidentReport` schemas, a single `AnalystAgent`, and deterministic `alert.type → runbook` routing all live at the center. Transport concerns are scattered at the package root (`src/mcp_auth.py`, `src/mcp_tools.py`), and the MCP server is assembled inline in `src/api/app.py`. Adding a second triage domain today means overhauling the core rather than dropping in a module.

This change sets the **direction and project structure** for a modular multi-domain Benny. It is a design capture, not a committed implementation: delta specs and tasks are deferred to per-slice follow-up changes once the open questions in `design.md` are resolved.

## What Changes

Reframe Benny around a **horizontal / vertical** agent model plus a project restructure:

- **Vertical "analyst modules" (skills)** — one self-contained module per triage domain (SIEM, VM). Each owns its input contract, playbooks, an analyst agent that owns the investigation reasoning, and its output contract. Adding a domain becomes adding a module, not changing the core.
- **Horizontal "capability" layer** — cross-cutting competences shared by all modules: data access (DataAgent), identity/access (Okta), enrichment (threat intel). Analysts consume these as tools or sub-agents.
- **OrchestratorAgent** — a single entry serving both API (explicit domain) and MCP chat (free-form) via one seam `handle(request, hint=None)`: deterministic dispatch when the domain is known, LLM classification when it must be inferred. Routes to one module for MVP, with a return type that allows cross-module synthesis to be added later behind the same interface.
- **Compression-boundary costing rule** — codify when a unit is an LLM sub-agent vs a composite deterministic tool vs an inline tool, so the agent tree does not quietly become an expensive N-deep nest.
- **Project restructure** — introduce `core/` (shared spine), `capabilities/` (horizontals), `modules/` (verticals), and move MCP concerns out of the package root into `mcp/server/` (Benny as an MCP server for clients) and `mcp/clients/` (Benny as a client of external MCP servers, e.g. ClickHouse via stdio).

## Capabilities

### New Capabilities
- `project-structure` **(specced + built in this change — slice 1)**: the horizontal/vertical package layout (`core/` / `capabilities/` / `modules/`) and the MCP transport reorg (`mcp/server`, `mcp/clients`), as a behavior-preserving refactor
- `analyst-module-contract` *(follow-up change)*: the module abstraction (input contract, playbooks, analyst agent, output contract, declared capability needs) and a module registry the orchestrator routes over
- `agent-orchestration` *(follow-up change)*: OrchestratorAgent routing across modules for both the API and MCP-chat entry points
- `capability-layer` *(follow-up change)*: horizontal capability agents/tools (data, identity, enrichment) shared across modules
- `agent-cost-principles` *(follow-up change)*: the compression-boundary rule codified as project guidance

### Modified Capabilities
- `multi-datasource-routing`: the single `AnalystAgent` generalizes into a per-module analyst; DataAgent becomes a horizontal capability rather than a SIEM-owned component
- `okta-idp-integration`: `lookup_user` is promoted from an `AnalystAgent` method to a shared identity capability (composite tool now, IDPAgent later)

### Non-Goals
- Implementing the Vulnerability Management module (this change sets the frame; VM is a follow-up)
- Pinning exact method signatures — the architectural decisions are made (see design.md); precise APIs and edge cases land in the per-slice delta specs
- Changing LLM providers, persistence, or the ReAct loop mechanics
- Writing detailed delta specs and tasks (deferred to per-slice follow-up changes)

## Impact

- **New top-level packages:** `src/core/`, `src/capabilities/`, `src/modules/`, `src/mcp/server/`, `src/mcp/clients/`
- **Moves (indicative):**
  - `src/mcp_auth.py` → `src/mcp/server/auth.py`
  - `src/mcp_tools.py` → `src/mcp/server/tools.py`; MCP-server assembly extracted out of `src/api/app.py` into `src/mcp/server/`
  - `src/agents/base_agent.py` → `src/core/agents/`
  - `src/orchestrator.py`, `src/runbook_registry.py` → `src/core/orchestration/`
  - `src/agents/data/` → `src/capabilities/data/`
  - `src/integrations/okta.py` (+ `user_profile` schema) → `src/capabilities/identity/`
  - `src/agents/analyst_agent.py`, `src/agents/detection_engineer_agent.py`, `runbooks/`, and SIEM envelope schemas (`alert`, `incident_report`) → `src/modules/siem/`
- **Contract generalization:** `Alert` / `IncidentReport` become the SIEM module's domain schemas; `Investigation` moves to `core/` as an idempotency envelope (module-supplied dedup key + generic `outcome`, domain-specific `report` payload) so "each alert or finding is reviewed once" is enforced uniformly across modules
- **First slice is a pure refactor** — the restructure + MCP move can land with no behavior change and tests green, before any new module is added
- **Follow-up changes:** (1) project restructure + MCP move; (2) module contract + registry + OrchestratorAgent; (3) identity capability extraction; (4) VM module
