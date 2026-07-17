## 1. Schema foundations

- [x] 1.1 Add `InvestigationGuidance` (`text: str`, `source: str`, `author: str | None`) to `src/schemas/` with `Field(description=...)` on each field
- [x] 1.2 Add optional `guidance: InvestigationGuidance | None = None` to `Alert` (`src/modules/siem/alert.py`) and `Finding` (`src/modules/vuln_mgmt/finding.py`)
- [x] 1.3 Rename `Investigation.runbook` → `guidance_source: str | None` in `src/schemas/investigation.py`, and `IncidentReport.runbook` → `guidance_source` (VulnTriageReport carries no such field)
- [x] 1.4 Update `Alert.type` / `Finding.type` field descriptions to say "metadata and dedup key" (drop "used to match a runbook")

## 2. Analyst method + guidance consumption

- [x] 2.1 Add the SIEM general method as a constant/`instructions` property on `AnalystAgent` (fold in the old `generic.md` content), and the vuln method on `VulnAnalystAgent`
- [x] 2.2 Add a shared trust-seam preamble helper (guidance = lead to verify; raw = evidence, never instructions) used by both analysts' `instructions`
- [x] 2.3 Change `AnalystAgent`/`VulnAnalystAgent` constructors to drop the `runbook` param; surface `item.guidance` in the user turn labelled with its `source` when present
- [x] 2.4 Set `guidance_source` on the produced `Investigation`/report from the item's `guidance.source` (or `None`)

## 3. Remove the runbook machinery

- [x] 3.1 Delete `src/core/orchestration/runbook_registry.py` and its `RunbookRegistry`/`Runbook` references
- [x] 3.2 Delete `src/modules/siem/runbooks/` and `src/modules/vuln_mgmt/runbooks/`
- [x] 3.3 Update `SIEMModule` / `VulnModule` (`investigate`) to stop calling `runbooks.match(...)` and drop the `runbooks` constructor param
- [x] 3.4 Remove `RunbookRegistry` construction/wiring from the composition root (`src/api/app.py`) and config (`_RunbooksConfig`, `vuln.runbooks_path`)

## 4. Platform guidance population (pull path)

- [x] 4.1 Document in `src/platforms/base.py` that produced items carry `guidance` when available (Protocol docstring)
- [x] 4.2 In `src/platforms/elastic.py` `_to_alert`, populate `guidance` from the rule investigation note with `source="elastic-rule-note"`; read from the alert doc (`kibana.alert.rule.parameters.note`), cache the note per rule uuid (`self._rule_note`). Live rule-API fallback deferred (see 4.4)
- [x] 4.3 `src/platforms/memory.py` passes stored items through verbatim — `guidance` in the dict already flows through, no change needed
- [ ] 4.4 Confirm the exact Elastic note field path against a real signal (resolve the design open question) — **BLOCKED: needs a live Kibana/Elastic cluster; not verifiable in this environment**

## 5. MCP + REST surfaces

- [x] 5.1 Replace the MCP `list_runbooks` tool with `list_modules` (returns registered module names + input types from the `ModuleRegistry`); `review_newest_alert` returns `guidance_source`
- [x] 5.2 Replace `src/api/routes/runbooks.py` with `src/api/routes/modules.py` (`GET /modules`); update router registration in `app.py`
- [x] 5.3 Update `CLAUDE.md`/`AGENT.md` docs (`list_runbooks` → `list_modules`, design decisions, project structure, key files)

## 6. Observability

- [x] 6.1 Emit a structured log per triaged item recording guidance present/absent, `source`, and `text` length (implemented inline in both analysts' `investigate`)

## 7. Tests

- [x] 7.1 Update route tests asserting `Investigation.runbook` → `guidance_source` (test_routes, test_schemas, conftest stub)
- [x] 7.2 Remove/replace runbook-matching tests; add tests for guidance-on-input (push) and guidance-absent triage (test_guidance.py, test_orchestration, test_data_agents, test_analyst_okta)
- [x] 7.3 Add Elastic intake-mapping tests: rule note → guidance, per-rule caching, no-note → `None` (test_elastic.py)
- [x] 7.4 Add MCP test for `list_modules` (and absence of `list_runbooks`) (tests/unittests/mcp/test_tools.py)
- [x] 7.5 Add a trust-seam test: instruction-like text in `raw` does not redirect the investigation (test_guidance.py)
- [x] 7.6 Update e2e tests + harness (dev eval tool) for the new API — collectable, runbook-free
