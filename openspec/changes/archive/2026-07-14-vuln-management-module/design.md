# Design: Vulnerability Management module

## Context

VM is Benny's second triage vertical and the real test of the `AnalystModule` contract shipped in `module-contract-and-orchestrator`. It is structurally identical to SIEM triage (investigate an input against playbooks + corporate context → verdict) but with different tooling: asset/vuln *state* + threat-intel enrichment instead of high-volume logs.

Two decisions were settled up front:
- **The report-payload generalization is folded in.** `Investigation.report` is currently typed as the SIEM `IncidentReport` (the last persistence→module edge). VM produces a different report, so this change generalizes the envelope.
- **Dev-stub data/intel.** The first VM module proves the contract end-to-end using a seeded SQLite asset/vuln store and a stub intel capability — real CVE/EPSS/KEV API clients are deferred.

## Goals / Non-Goals

**Goals:**
- A `vuln_mgmt` module implementing the `AnalystModule` contract end-to-end (input, playbooks, analyst, report, dedup key)
- Generalize the `Investigation` envelope so any module's report fits, removing the last persistence→module edge
- Prove routing: reachable via `OrchestratorAgent` and idempotent via `dedup_key`
- SIEM behavior unchanged; suite stays green

**Non-Goals:**
- Real CVE / EPSS / KEV API clients and a real asset-inventory backend (stub/SQLite for now)
- Remediation actions (Benny is investigation-only)
- Async execution / claim lifecycle (inherited sync model)

## Decisions

### D1. Generalize the Investigation envelope (report → opaque payload + generic Outcome)
- `Investigation.report` becomes `dict[str, object] | None` — a serialized, domain-agnostic payload. Each module keeps its **typed** report internally and dumps it to the envelope (`report.model_dump(mode="json")`). This removes the `schemas/investigation.py → modules/siem` import edge.
- Add `Investigation.outcome: Outcome | None` where `Outcome` is a **core** type (`disposition: str`, `priority: str`) — the cross-domain summary enabling listing across SIEM + VM without deserializing reports.
- Keep the existing `severity`/`verdict`/`runbook` fields as optional (SIEM continues to set them; VM leaves them `None`). Fully removing them is a later cleanup.
- *Alternative considered:* a typed discriminated union `report: IncidentReport | VulnTriageReport`. Rejected — it would force `core` to import every module's report type, reintroducing the core→modules edge.

### D2. Finding — the VM input contract
Mirrors `Alert` so it fits the module pattern:
`id`, `type` (vuln class → runbook match), `cve`, `asset`, `cvss: float`, `title`, `description`, `source` (scanner), `detected_at: datetime`, `raw: dict`.

### D3. Dedup key = `cve:asset:cvss`
`VulnModule.dedup_key(finding)` → `f"{finding.cve}:{finding.asset}:{finding.cvss}"`. A CVSS rescoring busts the key → the finding is re-reviewed; an unchanged rescan is deduped. (Later, KEV/EPSS state can feed the hash.) The orchestrator namespaces it as `vuln_mgmt:<key>`.

### D4. VulnTriageReport — the VM output
`finding_id`, `exploitable: bool`, `priority: str`, `remediation_sla_days: int | None`, `confidence: float`, `summary`, `affected_assets: list[str]`, `evidence: list[str]`, `recommended_actions: list[str]`, `investigation_steps: list[str]`. The module maps it onto the generic `Outcome` (`disposition` = exploitable?, `priority`).

### D5. Data — reuse the DataAgent/QueryEngine pattern (dev SQLite)
The asset/vuln inventory is a `SQLiteDataAgent` over a seeded dev DB, registered in `Capabilities.data["asset_inventory"]`. The VM analyst selects it via `caps`. No new engine — same pattern as SIEM's `security_logs`.

### D6. Vuln intel — a VM-owned composite tool (stub)
Threat-intel enrichment (CVE/EPSS/KEV) is **vertical tooling** owned by the VM module (per the horizontal/vertical model: enrichment *sources* are domain-specific). It is a composite deterministic tool (compression-boundary rule: fixed lookups → tool, not sub-agent), exposed to the VM analyst. Dev impl returns stub/empty enrichment; real API clients are a follow-up.

### D7. Playbooks and routing
VM runbooks live in `src/modules/vuln_mgmt/runbooks/`, matched by `finding.type` (vuln class) with a `generic` fallback — same mechanism as SIEM, internal to the module. `create_app` registers `VulnModule` in the `ModuleRegistry`. A new `POST /findings` route calls `orchestrator.handle(raw, hint="vuln_mgmt")`; `accepts()` enables free-form MCP routing later.

## Risks / Trade-offs

- **Report as `dict` loses envelope-level typing** → Accepted: the envelope is domain-agnostic by design; modules own their typed reports; API responses were already JSON. Mitigated by the typed `Outcome` for the fields that matter cross-domain.
- **Touching SIEM (report→dict)** → The generalization changes how SIEM builds `Investigation`. Mitigation: parity is the bar — existing SIEM tests must stay green; SIEM dumps its `IncidentReport` to the envelope.
- **Stub intel gives shallow verdicts** → Accepted for a contract-proving first module; real intel is the obvious follow-up.
- **Two data agents built at startup** → `create_app` now builds both `security_logs` and `asset_inventory` (dev). Fine; config-gated later.

## Migration Plan

1. Generalize the envelope (`report: dict`, add `Outcome`); update SIEM to dump its report + set `outcome`; keep SIEM tests green.
2. Add `modules/vuln_mgmt/`: `Finding`, `VulnTriageReport`, runbooks, `VulnModule` (accepts/dedup_key/investigate), a VM analyst, and the stub intel tool.
3. Wire `create_app`: seed/build the `asset_inventory` data agent, register `VulnModule`; add `POST /findings`.
4. Tests: VM unit tests (accepts, dedup_key, routing), a `/findings` route test, and an e2e VM investigation (skipped without API key). Full suite green.

## Open Questions

- Exact asset identity (hostname vs asset-id vs IP) for `Finding.asset` and the dedup key — dev uses a free-form string; formalize when a real inventory lands.
- Whether `Outcome.disposition`/`priority` should become small shared enums vs free strings — strings now for cross-domain flexibility.
- Whether SIEM should fully migrate off `severity`/`verdict`/`runbook` onto `outcome` — deferred cleanup.
