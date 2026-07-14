## 1. Baseline & safety net

- [x] 1.1 Confirm slice 1 (`modular-soc-architecture`) is merged — the `core/ · capabilities/ · modules/siem/` structure must exist
- [x] 1.2 Run `make test` and `make lint` and record a green baseline (the SIEM `/investigate` behavior is the parity reference)
- [x] 1.3 Create a working branch for slice 2

## 2. Core contracts (additive — no behavior change yet)

- [x] 2.1 Add `src/core/orchestration/capabilities.py` — a typed `Capabilities` container: `data: dict[str, BaseDataAgent]` plus an optional identity field, instances only
- [x] 2.2 Add `src/core/orchestration/module.py` — the `AnalystModule` Protocol (`name`, `input_type`, `accepts(raw) -> bool`, `investigate(inp, caps) -> Investigation`); do NOT add `dedup_key` (deferred to `investigation-idempotency`)
- [x] 2.3 Add `src/core/orchestration/module_registry.py` — `ModuleRegistry` with `register`, `get(name)`, `resolve(raw)` via `accepts()`; raise `ValueError` on duplicate names
- [x] 2.4 Unit-test the registry (register/get/resolve, duplicate-name rejection) in isolation

## 3. SIEM as the first module

- [x] 3.1 Add `src/modules/siem/module.py` — `SIEMModule` implementing `AnalystModule`: `name="siem"`, `input_type=Alert`, `accepts()` for alert-shaped payloads
- [x] 3.2 Implement `SIEMModule.investigate(alert, caps)` — match the runbook by `alert.type` (via the SIEM-internal `RunbookRegistry`), construct `AnalystAgent(runbook, data_agents=list(caps.data.values()), okta_client=caps.identity)`, run, and return the `Investigation`
- [x] 3.3 Relocate runbook loading so it is owned by the SIEM module (SIEM keeps its own `RunbookRegistry`; `ModuleRegistry` is separate)
- [x] 3.4 Unit-test `SIEMModule.accepts()` and that `investigate` matches the runbook (known type → that runbook; unknown → `generic`)

## 4. OrchestratorAgent

- [x] 4.1 Replace `src/core/orchestration/orchestrator.py`'s `Orchestrator` with `OrchestratorAgent.handle(raw, hint=None) -> Investigation | None`
- [x] 4.2 Implement resolution: `hint` present → `registry.get(hint)` (no LLM); absent → `registry.resolve(raw)`; return `None` when unresolved
- [x] 4.3 Delegate to `module.investigate(module.input_type(**raw), caps)`, persist the result, and return it
- [x] 4.4 Define the return type so a future synthesized multi-module result needs no `handle()` signature change (router-now)
- [x] 4.5 Remove the direct `AnalystAgent` / `Alert` imports from `core/orchestration/` — the transitional `core → modules` edge is now gone
- [x] 4.6 Unit-test `handle`: hint path makes no classifier call; single-module free-form resolves; unresolved → `None`; result persisted

## 5. Composition-root wiring

- [x] 5.1 In `create_app`, build the `Capabilities` container from the initialized data agents (+ Okta) that the lifespan already constructs
- [x] 5.2 Instantiate `ModuleRegistry`, construct and register `SIEMModule`, and build `OrchestratorAgent` with the registry, capabilities, and persistence
- [x] 5.3 Point `POST /investigate` at `OrchestratorAgent.handle(raw, hint="siem")`; map an unresolved result to the existing `422` response
- [ ] 5.4 Ensure the MCP tools and the REST orchestrator share the same `Capabilities` instance (built once)

## 6. Verify parity & invariants

- [x] 6.1 `make test` green — existing SIEM `/investigate` and route tests pass, plus the new contract/registry/orchestrator unit tests
- [x] 6.2 `make lint` clean
- [x] 6.3 Spot-check runtime: submit an alert and confirm the `Investigation`/`IncidentReport` structure and `runbook` matching are unchanged from slice 1
- [x] 6.4 Grep the import graph: `core/orchestration/` no longer imports `modules/`; only the composition root (`api/app.py`) imports `modules/` (to register `SIEMModule`)

## 7. Docs & PR

- [x] 7.1 Update `CLAUDE.md` — describe the module contract, `OrchestratorAgent`, and the `Capabilities` layer; update "Key Files"
- [ ] 7.2 Final `make test` + `make lint`, then open the slice-2 PR
