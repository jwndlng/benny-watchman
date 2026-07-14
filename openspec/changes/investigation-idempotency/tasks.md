## 1. Dedup key on the contract

- [x] 1.1 Add `dedup_key(inp) -> str` to the `AnalystModule` Protocol
- [x] 1.2 Implement `SIEMModule.dedup_key(alert)` → `alert.id`

## 2. Investigation envelope + persistence

- [x] 2.1 Add `key` and `module` fields to `Investigation` (default empty)
- [x] 2.2 Add `InvestigationModel.find_by_key(key)` (scan-based lookup)

## 3. Orchestrator dedup + API idempotency

- [x] 3.1 `OrchestratorAgent.handle` namespaces the key, checks `find_by_key`, returns existing on hit, else runs + tags + persists
- [x] 3.2 `handle` returns `HandleResult(investigation, created)`
- [x] 3.3 `POST /investigate` returns 202 (fresh) / 200 (cached); duplicate yields one stored investigation

## 4. Tests & verify

- [x] 4.1 Unit-test dedup hit (returns existing, no re-run, no save) and SIEM dedup key
- [x] 4.2 Route test: same alert twice → 202 then 200, same id, one stored
- [x] 4.3 `make test` green, `make lint` clean

## 5. Deferred (out of scope — noted in design)

- [ ] 5.1 Generic `outcome` + report-payload generalization (removes the persistence→module edge)
- [ ] 5.2 Claim lifecycle (PENDING/RUNNING) + async execution for concurrent-duplicate safety
