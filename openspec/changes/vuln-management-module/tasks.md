## 1. Baseline

- [x] 1.1 Confirm the transition is merged/available (module contract, orchestrator, idempotency) and `make test` is green
- [x] 1.2 Create a working branch

## 2. Generalize the Investigation envelope

- [x] 2.1 Add a core `Outcome` type (`disposition: str`, `priority: str`) in `src/schemas/` (or `src/core/`)
- [x] 2.2 Change `Investigation.report` to `dict[str, object] | None` and add `outcome: Outcome | None`; remove the `IncidentReport` import from `src/schemas/investigation.py`
- [x] 2.3 Update SIEM `AnalystAgent.investigate` to dump its `IncidentReport` into `report` and set `outcome` (map verdict→disposition, severity→priority)
- [x] 2.4 Update `conftest._stub_investigation` and any tests that build `Investigation` with a typed report
- [x] 2.5 Verify: `src/schemas/investigation.py` and `src/models.py` no longer import `src/modules/`; SIEM suite green; `/reports` responses unchanged

## 3. VM module

- [x] 3.1 Add `src/modules/vuln_mgmt/finding.py` (`Finding`) and `report.py` (`VulnTriageReport`)
- [x] 3.2 Add `src/modules/vuln_mgmt/runbooks/` with a `generic` runbook and at least one vuln-class runbook
- [x] 3.3 Add the VM analyst (ReAct loop, output = `VulnTriageReport`) reusing `BaseAgent`
- [x] 3.4 Add the VM-owned vuln-intel composite tool (stub CVE/EPSS/KEV enrichment)
- [x] 3.5 Add `src/modules/vuln_mgmt/module.py` (`VulnModule`): `name`, `input_type=Finding`, `accepts`, `dedup_key` = `cve:asset:cvss`, `investigate` (match runbook → build analyst from `caps` + intel tool → run → map `outcome`)

## 4. Data + wiring

- [x] 4.1 Add a seeded SQLite asset/vuln dataset (dev) and expose it as a `SQLiteDataAgent` named `asset_inventory`
- [x] 4.2 `create_app`: build the `asset_inventory` data agent into `Capabilities.data`; register `VulnModule` in the `ModuleRegistry`
- [x] 4.3 Add `POST /findings` → `orchestrator.handle(raw, hint="vuln_mgmt")` (202 fresh / 200 dedup / 422 unresolved)

## 5. Tests & verify

- [x] 5.1 Unit-test `VulnModule.accepts` (finding vs non-finding) and `dedup_key`
- [x] 5.2 Route test for `POST /findings`: fresh 202, duplicate 200 (same id, one stored)
- [x] 5.3 e2e VM investigation (skipped without API key), mirroring the SIEM e2e
- [x] 5.4 `make test` green (SIEM + VM), `make lint` clean
- [x] 5.5 Update `AGENT.md` — add the VM module to the structure/module list

## 6. Deferred (out of scope — noted in design)

- [ ] 6.1 Real CVE / EPSS / KEV API clients and a real asset-inventory backend
- [ ] 6.2 Full removal of `severity`/`verdict`/`runbook` from the envelope in favor of `outcome`
