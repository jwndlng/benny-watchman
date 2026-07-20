## 1. Baseline & safety net

- [x] 1.1 Run `make test` and record the pass count — this is the behavior-preservation reference (147 passed)
- [x] 1.2 Run `make lint` and confirm a clean baseline
- [x] 1.3 Create a working branch off `main` for the refactor

## 2. Create the new package skeleton

- [x] 2.1 `capabilities/subagents/` and `capabilities/tools/` (with `__init__.py`)
- [x] 2.2 `modules/siem/schemas/`, `modules/vuln_mgmt/schemas/`, `modules/vuln_mgmt/tools/` (with `__init__.py`)
- [x] 2.3 `adapters/` and `adapters/mcp/` (with `__init__.py`); the leaf packages (`api`, `mcp/server`, `mcp/clients`, `platforms`, `engines`) arrive via `git mv` in §5

## 3. Split capabilities by boundary kind

- [x] 3.1 `git mv src/capabilities/data/* src/capabilities/subagents/data/` (base_data_agent, sqlite_, elastic_, query_tool)
- [x] 3.2 `git mv src/capabilities/identity/* src/capabilities/tools/identity/` (assessment, okta, user_profile)
- [x] 3.3 Remove the now-empty `src/capabilities/data/` and `src/capabilities/identity/` package dirs

## 4. Make modules self-contained

- [x] 4.1 `git mv src/modules/siem/{alert,incident_report}.py src/modules/siem/schemas/`
- [x] 4.2 `git mv src/modules/vuln_mgmt/{finding,report}.py src/modules/vuln_mgmt/schemas/`
- [x] 4.3 `git mv src/modules/vuln_mgmt/intel.py src/modules/vuln_mgmt/tools/intel.py`

## 5. Group the outer I/O ring under adapters/

- [x] 5.1 `git mv src/api src/adapters/api`
- [x] 5.2 `git mv src/mcp src/adapters/mcp` (preserves `server/` and `clients/`)
- [x] 5.3 `git mv src/platforms src/adapters/platforms`
- [x] 5.4 `git mv src/engines src/adapters/engines`
- [x] 5.5 `git mv src/models.py src/adapters/persistence.py`

## 6. Delete unwired stubs

- [x] 6.1 Delete `src/capabilities/enrichment/` (EnrichmentAgent — never instantiated)
- [x] 6.2 Delete `src/modules/siem/reviewer.py` and `src/modules/siem/detection_engineer.py` (never instantiated)
- [x] 6.3 Grep for any lingering references to the deleted classes and remove them (none found)

## 7. Rewrite imports (fixed rename map)

- [x] 7.1 Apply the rename map across `src/`, `tests/`, and `main.py` (48 files rewritten):
  - `src.engines` → `src.adapters.engines`
  - `src.platforms` → `src.adapters.platforms`
  - `src.models` → `src.adapters.persistence`
  - `src.api` → `src.adapters.api`
  - `src.mcp` → `src.adapters.mcp`
  - `src.capabilities.data` → `src.capabilities.subagents.data`
  - `src.capabilities.identity` → `src.capabilities.tools.identity`
  - `src.modules.siem.alert` / `.incident_report` → `src.modules.siem.schemas.*`
  - `src.modules.vuln_mgmt.finding` / `.report` → `src.modules.vuln_mgmt.schemas.*`
  - `src.modules.vuln_mgmt.intel` → `src.modules.vuln_mgmt.tools.intel`
- [x] 7.2 Update `main.py` entry import to `from src.adapters.api.app import create_app`
- [x] 7.3 Let `ruff` surface any unresolved/unused imports; fix stragglers (ruff format reordered 2 files; clean)

## 8. Mirror tests + refresh docs

- [ ] 8.1 (DEFERRED for review) Mirror the test package layout to the new tree — the current `tests/unittests/{agents,integrations,platforms,engines,capabilities}` grouping doesn't map 1:1 (organizes by feature area, not source path), so relocation is left for review guidance. Tests pass in place with import paths updated.
- [x] 8.2 Update `AGENT.md` (Project Structure + Key Files; `CLAUDE.md` is a symlink to it) and `README.md` (Architecture layout) to the new tree
- [x] 8.3 Confirm `RUNBOOKS_PATH` / `VULN_RUNBOOKS_PATH` defaults are unchanged (runbooks stay under the module) — no config change needed

## 9. Verify behavior preservation

- [x] 9.1 `make test` — 147 passed (matches baseline)
- [x] 9.2 `make lint` — clean
- [x] 9.3 Dependency-direction check (grep): `core/` imports nothing from `modules/`, and only a `TYPE_CHECKING` `InvestigationModel` hint from `adapters/`; `capabilities/` imports nothing from `modules/`; no cross-module imports
- [x] 9.4 Boot the app (`create_app` with a dummy model key) — app builds, 15 routes, unified logging intact
