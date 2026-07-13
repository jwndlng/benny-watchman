## 1. Baseline & safety net

- [x] 1.1 Run `make test` and confirm green — this is the behavior-preservation reference the refactor must not break
- [x] 1.2 Run `make lint` and confirm clean baseline
- [x] 1.3 Create a working branch for the slice-1 refactor

## 2. Create the package skeleton

- [x] 2.1 Create `src/core/`, `src/core/agents/`, `src/core/orchestration/` with `__init__.py`
- [x] 2.2 Create `src/capabilities/`, `src/capabilities/data/`, `src/capabilities/identity/`, `src/capabilities/enrichment/` with `__init__.py`
- [x] 2.3 Create `src/modules/`, `src/modules/siem/` with `__init__.py`
- [x] 2.4 Create `src/mcp/server/`, `src/mcp/clients/` with `__init__.py` (the `src/mcp/` package already exists)

## 3. Move the framework into core/

- [x] 3.1 Move `src/agents/base_agent.py` → `src/core/agents/base_agent.py`
- [x] 3.2 Move `src/orchestrator.py` → `src/core/orchestration/orchestrator.py`
- [x] 3.3 Move `src/runbook_registry.py` → `src/core/orchestration/runbook_registry.py` (keep the `RunbookRegistry` class name — the `ModuleRegistry` rename is slice 2)
- [x] 3.4 Note: the moved `Orchestrator` still imports the SIEM analyst — this transitional `core → modules` edge is allowed but MUST stay confined to `core/orchestration/`

## 4. Move horizontals into capabilities/

- [x] 4.1 Move `src/agents/data/*` → `src/capabilities/data/`
- [x] 4.2 Move `src/integrations/okta.py` → `src/capabilities/identity/okta.py` and `src/schemas/user_profile.py` → `src/capabilities/identity/user_profile.py`
- [x] 4.3 Move `src/agents/enrichment_agent.py` → `src/capabilities/enrichment/enrichment_agent.py`
- [x] 4.4 Verify no file under `src/capabilities/` imports from `src/modules/` (dependency-direction invariant)

## 5. Move the SIEM vertical into modules/siem/

- [x] 5.1 Move `src/agents/analyst_agent.py` → `src/modules/siem/analyst.py`
- [x] 5.2 Move `src/agents/detection_engineer_agent.py` → `src/modules/siem/detection_engineer.py` and `src/agents/reviewer_agent.py` → `src/modules/siem/reviewer.py` (reviewer depends on the SIEM `IncidentReport`; its horizontal-critic future is reconsidered post-contract)
- [x] 5.3 Move the SIEM schemas `src/schemas/alert.py` and `src/schemas/incident_report.py` → `src/modules/siem/`
- [x] 5.4 Move `runbooks/` (repo root) → `src/modules/siem/runbooks/` and update the `RUNBOOKS_PATH` default (config) / lifespan wiring to the new location
- [x] 5.5 Keep `Investigation` / `InvestigationModel` at their current shape and location (persistence) — do NOT reshape; update only their import of `IncidentReport`/`Severity`/`Verdict` to the new SIEM path (documented transitional persistence → module edge, resolved by `investigation-idempotency`)

## 6. Reorganize MCP transport

- [x] 6.1 Move `src/mcp_auth.py` → `src/mcp/server/auth.py`
- [x] 6.2 Move `src/mcp_tools.py` → `src/mcp/server/tools.py`
- [x] 6.3 Extract the FastMCP assembly out of `src/api/app.py` into `src/mcp/server/app.py` — a factory that builds the `FastMCP` instance, registers tools, and returns the ASGI app (plus bearer token handling)
- [x] 6.4 Update `src/api/app.py` to import the assembled server from `src/mcp/server/` and mount it — no inline `FastMCP` construction or tool registration remains in the API layer
- [x] 6.5 Add a placeholder (README or empty package) in `src/mcp/clients/` marking it as the future home for external MCP clients (e.g. ClickHouse)
- [x] 6.6 Confirm `src/mcp_auth.py` and `src/mcp_tools.py` no longer exist

## 7. Update imports & wiring

- [x] 7.1 Update all `src/` import statements to the new paths (use `make lint` / ruff and a grep for old module paths to find them)
- [x] 7.2 Update the `create_app` lifespan wiring (data agents, Okta, orchestrator, registry, MCP mount) to the new locations
- [x] 7.3 Verify `main.py` still boots (`create_app` path is unchanged, but confirm its transitive imports resolve)
- [x] 7.4 Update test imports to the new paths (`tests/unittests/agents/`, `integrations/`, `schemas/`, etc.); optionally mirror the new `core/capabilities/modules` layout in the test tree

## 8. Verify behavior preservation

- [x] 8.1 `make test` is green with changes limited to import paths — the pre-refactor passing tests all pass
- [x] 8.2 `make lint` is clean
- [x] 8.3 Spot-check runtime: `POST /investigate` behaves as before, and `list_runbooks` / `lookup_data` are served at `/mcp` with the same bearer auth and schemas
- [x] 8.4 Grep the import graph: `src/capabilities/` and `src/core/agents/` import nothing from `src/modules/`; the only `core → modules` import is the transitional orchestrator edge in `src/core/orchestration/`
- [x] 8.5 Confirm no MCP module remains at the `src/` root and the FastMCP assembly is no longer inline in `src/api/app.py`

## 9. Cleanup & docs

- [x] 9.1 Remove the now-empty legacy dirs (`src/agents/`, `src/agents/data/`, `src/integrations/`, and `src/schemas/` if emptied)
- [x] 9.2 Update `CLAUDE.md` — the "Key Files" list and the MCP section — to the new paths
- [ ] 9.3 Final `make test` + `make lint`, then open the slice-1 PR
