## Context

Benny should review each alert or finding once, but nothing enforced it: every `POST /investigate` ran a fresh investigation under a random id. This change adds the "review once" guarantee via a module-supplied dedup key.

## Goals / Non-Goals

**Goals:**
- `AnalystModule.dedup_key(inp)` + a namespaced key `<module>:<key>`
- `OrchestratorAgent` dedups: a repeat request returns the stored investigation instead of re-running
- `Investigation` carries `key` and `module`; `POST /investigate` is idempotent (202 fresh, 200 cached)

**Non-Goals (deferred):**
- **Generic `outcome` + report-payload generalization** — the cross-domain-listing reshape and dropping the SIEM-specific `severity`/`verdict`/`runbook` fields from the envelope. `Investigation.report` stays typed as the SIEM `IncidentReport` for now (the transitional persistence→module import edge remains).
- **Claim lifecycle (PENDING/RUNNING) and async execution** — deferred per the sync decision. Dedup is sequential; two *simultaneous* identical submits could still race (both miss the lookup and run). Acceptable for now.

## Decisions

- **200 vs 202:** a freshly-run investigation returns `202`; a dedup hit returns `200` with the stored investigation. Callers distinguish new from cached by status code. `handle()` returns a `HandleResult(investigation, created)` so the route can pick the code — this is the "richer return type" the orchestrator design anticipated.
- **Key namespacing:** `<module>:<module.dedup_key(inp)>` so keys can't collide across modules. SIEM keys on `alert.id`.
- **Lookup:** `InvestigationModel.find_by_key` scans `list()` — O(n), acceptable at current volume; a ClickHouse backend replaces it with an indexed query.
- **Synchronous:** the investigation runs inline (as before); only the dedup check + tagging are added.

## Risks / Trade-offs

- **Scan-based lookup** → O(n) per request. Fine now; note for the ClickHouse migration.
- **Sequential-only dedup** → a concurrent duplicate can double-run. Mitigation deferred to the claim-lifecycle/async change.
- **Envelope still SIEM-shaped** → the generic-`outcome` reshape is a follow-up; this change is scoped to the dedup guarantee.
