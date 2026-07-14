## Why

Benny should review each alert or finding **once**, but today it does not: `Orchestrator.investigate()` always runs a fresh investigation and persists it under a random `uuid4`, so a duplicate submission produces a duplicate investigation. The `PENDING`/`RUNNING` statuses exist in the enum but are never used, and `POST /investigate` returns `202` while running synchronously. This change makes "review once" real by turning `Investigation` into a core idempotency envelope.

This implements the "Investigation is a core idempotency envelope" decision recorded in the `modular-soc-architecture` design.

## What Changes

- **Core owns the machinery; the module owns the policy.** `core` provides claim-by-key → run → save → return-existing; the module supplies the key and staleness rule.
- **Module-supplied dedup key.** `AnalystModule.dedup_key(inp)` determines identity. SIEM uses `alert.id` (review once per firing — recurrence arrives as a new alert id → a new investigation); VM will use `(cve, asset, content-hash)` so a materially changed finding (now in KEV, CVSS ↑) busts the key and is re-reviewed.
- **Claim lifecycle.** Insert a `RUNNING` record keyed by `dedup_key` *before* dispatching, so a concurrent duplicate submit sees the in-flight claim and returns/waits instead of racing a parallel run. `PENDING`/`RUNNING`/`COMPLETE`/`FAILED` become meaningful; without a claim step, dedup catches only sequential repeats.
- **Generic outcome + domain report.** Replace the SIEM-specific `severity`/`verdict`/`runbook` currently hoisted onto `Investigation` (and duplicated inside `report`) with a generic `outcome` (disposition + priority) every domain maps onto — enabling cross-domain listing without deserializing each report — while the domain-specific `report` becomes a typed payload.
- **Scope boundary.** Dedup applies to the formal triage path (a filed alert/finding), not the conversational MCP path ("ask Benny about user Y"), which is exploratory and not persisted-and-deduped.

## Capabilities

### New Capabilities
- `investigation-idempotency`: the core `Investigation` envelope, the claim lifecycle, and the once-only guarantee

### Modified Capabilities
- `multi-datasource-routing`: the orchestration flow claims by `dedup_key` and short-circuits on repeat instead of always constructing and running a fresh analyst

## Impact

- **Depends on:** `module-contract-and-orchestrator` (`dedup_key` is a module method). **Interim option:** a SIEM-only version keyed on `alert.id` could land *before* the contract exists and be generalized when it does — pull this forward if dedup matters sooner than the VM work.
- `src/core/`: `Investigation` envelope (`id`, `key`, `module`, `status`, `outcome`, `report`), claim-by-key persistence, status transitions
- `src/models.py`: upsert/claim semantics keyed on `dedup_key` rather than a random id
- API: `POST /investigate` returns the existing investigation on repeat; consider making the run asynchronous with `GET /investigations/{id}` polling (the `202` + status lifecycle finally align)
- Benny owns the "once" guarantee rather than pushing it upstream — with two entry points (API and MCP) and eventually multiple callers, Benny is the only place it holds
