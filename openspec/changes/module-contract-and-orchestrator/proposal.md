## Why

Slice 1 (`modular-soc-architecture` / `project-structure`) relocates code into the `core/ · capabilities/ · modules/` seam but introduces no new abstractions — the deterministic `Orchestrator` still imports the SIEM analyst directly, leaving a transitional `core → modules` edge. To add a second triage domain without overhauling the core, Benny needs a formal module abstraction and an orchestrator that routes to it.

The architectural decisions are already made in the `modular-soc-architecture` design (decisions 1–4); this change implements them and migrates SIEM to be the first module through the contract, inverting the transitional edge.

## What Changes

- **`AnalystModule` Protocol** — a typed contract each vertical implements: `name`, `input_type`, `report_type`, `accepts(raw) -> bool`, `dedup_key(inp) -> str`, `build_analyst(caps) -> Analyst`. (Decision 3: typed Protocol + explicit registration, chosen over directory-manifest and entry-point plugins to keep full static typing and match the existing `BaseAgent`/`BaseDataAgent` style.)
- **`ModuleRegistry`** — generalizes `RunbookRegistry`; modules are registered explicitly at startup; playbooks stay folder-based *inside* each module.
- **`OrchestratorAgent`** — a single seam `handle(request, hint=None)`: explicit domain (API passes a `hint`) → direct dispatch with no LLM; free-form (MCP chat, no hint) → LLM classification via each module's `accepts()`. (Decision 2: one entry, two speeds, short-circuit inside the orchestrator.) Routes to exactly one module for now; the return type is designed to also carry a synthesized multi-module answer so lead-analyst behavior drops in later without a rewrite. (Decision 1: router now, lead-analyst later.)
- **`Capabilities` registry** — startup builds all capability instances centrally (backends are ops config, already in `config.py`) and passes a typed `Capabilities` object to `build_analyst(caps)`; each module selects the instances it consults (e.g. `caps.data["logs"]`). (Decision 4: typed registry the module selects from, no DI framework.)
- **SIEM as the first module** — `AnalystAgent` (+ its runbooks and `Alert`/`IncidentReport`) is wrapped in a `SIEMModule` implementing the contract; the deterministic `Orchestrator` is replaced by `OrchestratorAgent`, removing the transitional `core → modules` edge from slice 1.

## Capabilities

### New Capabilities
- `analyst-module-contract`: the `AnalystModule` Protocol + `ModuleRegistry`
- `agent-orchestration`: `OrchestratorAgent` two-speed routing across modules
- `capability-layer`: the `Capabilities` registry + `build_analyst(caps)` injection

### Modified Capabilities
- `multi-datasource-routing`: `AnalystAgent` is no longer constructed directly by the orchestrator; it becomes the SIEM module's analyst, built via `build_analyst(caps)` and reached through `OrchestratorAgent` + `ModuleRegistry`

### Non-Goals
- The idempotency envelope reshape (own change: `investigation-idempotency`)
- Extracting identity into a shared capability (own change: `identity-capability`)
- Any new triage domain (own change: `vuln-management-module`)

## Impact

- **Depends on:** `modular-soc-architecture` slice 1 (the package structure must exist)
- `src/core/orchestration/`: `Orchestrator` → `OrchestratorAgent`; `RunbookRegistry` → `ModuleRegistry`; add `module.py` (`AnalystModule` Protocol) and `capabilities.py` (`Capabilities`)
- `src/modules/siem/`: add a `SIEMModule` implementing the contract
- `src/api/routes/investigate.py` and the MCP entry: call `OrchestratorAgent.handle(...)` with a `hint` (API) or without one (chat)
- No change to the ReAct loop mechanics, LLM providers, or the persistence *shape* (that is `investigation-idempotency`)
