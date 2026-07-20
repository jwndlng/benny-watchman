## Context

`run_once` ([src/adapters/platforms/loop.py](../../../src/adapters/platforms/loop.py)) drives the triage cycle: `fetch_open` → `handle` → write-back. Today it acknowledges nothing — an alert stays `OPEN` for the entire investigation, and the terminal write is a `CLOSED`/`ESCALATED` binary ([base.py `TriageStatus`](../../../src/adapters/platforms/base.py)) that discards the analyst's disposition.

Constraints that shape this design:
- **Boundary discipline** — write-back is the platform's job; `core/` must stay unaware of it. The loop stays domain-agnostic (drives only `handle` + generic `outcome`).
- **Idempotency** — write-back happens only for a freshly-created investigation (`result.created`); dedup hits and unresolved items must not double-write.
- **Two implementations** — `InMemoryTriagePlatform` (dev) and `ElasticSecurityPlatform` (Kibana) must both satisfy any contract change.
- **Elastic reality** — the alert workflow status is `open | acknowledged | closed`; today `ESCALATED → acknowledged`, which collides with using `acknowledged` to mean "in progress."

Disposition vocabulary in play: SIEM verdicts are `true_positive | false_positive | inconclusive` ([incident_report.py](../../../src/modules/siem/schemas/incident_report.py)); VM adds `exploitable | not_exploitable`. `outcome.disposition` carries the mapped label.

## Goals / Non-Goals

**Goals:**
- Claim each alert (`acknowledge`) *before* investigating, so an in-flight item leaves the open queue and shows "someone is on it."
- Terminal state is **close-with-reason** derived from disposition, replacing the `CLOSED`/`ESCALATED` binary.
- Keep the write-back sequence in **one shared helper**; `run_once` becomes a thin fetch + loop. Add only the minimal contract surface.
- Preserve idempotency and the domain-agnostic loop.

**Non-Goals:**
- No change to how investigations reach a verdict (analyst/orchestrator untouched).
- No remediation — Benny still only investigates and annotates.
- No new triage platform; only the contract + existing two implementations change.
- Not resolving the exact Elastic close-reason API field here (spike; see Open Questions).

## Decisions

### D1 — Ownership: shared helper + thin `run_once`, one new primitive
The per-item sequence (acknowledge → handle → create_case → comment → set_severity → close-with-reason) lives in a single shared function in `loop.py`, reused by every platform. `run_once` only fetches and loops. The Protocol gains **one** new primitive, `acknowledge(item_id)`; the terminal write is expressed as close-with-reason (see D4).

_Alternative — `platform.triage()` method (the original suggestion):_ every platform would reimplement the case/comment/close sequence. Rejected: it duplicates domain-agnostic orchestration into each adapter and pushes `handle` awareness into the platform, breaking the "platforms do I/O, the loop orchestrates" seam.

### D2 — State model: `OPEN → ACKNOWLEDGED → CLOSED(reason)`; retire `ESCALATED`
`TriageStatus` becomes `OPEN`, `ACKNOWLEDGED`, `CLOSED`. `ACKNOWLEDGED` is the "Benny is on it" state set at start. `CLOSED` is terminal and always carries a **close reason**. `ESCALATED` is removed as a status — escalation is a property of the *case*, not the alert queue (see D5).

_Alternative — keep `ESCALATED` and leave true positives open:_ matches today's behavior but contradicts the agreed "always ack → close with a reason" flow, and keeps the `acknowledged`-means-two-things collision.

### D3 — Ack placement and edge cases
`acknowledge(item_id)` is called at the top of each iteration, immediately before `handle` (matching the intended flow "ack the alert and start investigating"). `run_once` always passes a `hint`, so the handling module is already committed. Edge cases after `handle`:
- **Dedup hit** (`not result.created`): close with reason **`DUPLICATE`**. This fixes a latent issue — today dedup hits are skipped and left `OPEN`, so they are re-fetched and re-handled every run.
- **No investigation** (`result.investigation is None`): leave the item `ACKNOWLEDGED` and log — Benny couldn't produce a verdict, so a human should see it rather than have it silently closed.

### D4 — Close-reason vocabulary + disposition mapping
Add a `CloseReason` enum and map `outcome.disposition` → reason:

| Source | `CloseReason` |
|---|---|
| dedup hit | `DUPLICATE` |
| `false_positive` | `FALSE_POSITIVE` |
| `benign`, `not_exploitable` | `BENIGN_POSITIVE` |
| `true_positive`, `exploitable` | `TRUE_POSITIVE` |
| `inconclusive` / unknown | `OTHER` |
| (no disposition) | `NONE` (close without reason) |

The terminal write is expressed as `set_status(item_id, CLOSED, reason=<CloseReason>)` — a signature extension (one new optional param) rather than a brand-new method, honoring "add only `acknowledge()`." `acknowledge` and the reason enum are the only genuinely new surface.

_Alternative — dedicated `close(item_id, reason)` method:_ reads slightly cleaner but adds a second new method; deferred in favor of the minimal surface.

### D5 — Escalation via the case, not the alert status
A `TRUE_POSITIVE` close still creates a case, sets case severity from `outcome.priority`, and tags it (`benny:escalate`). The human works the **case queue**, not the alert queue. This keeps the alert lifecycle clean (everything Benny touches ends `CLOSED`) while preserving a durable, auditable escalation surface.

### D7 — The case has its own lifecycle (open → in-progress → closed)
The case mirrors Benny's work, in parallel with the alert's `open → acknowledged → closed`: it is opened on creation, moved to `IN_PROGRESS` while triaging, and moved to `CLOSED` only when Benny **resolves** it (benign — `FALSE_POSITIVE`/`BENIGN_POSITIVE`). An escalated (true-positive) case is deliberately left `IN_PROGRESS` so it stays on a human's active queue — consistent with D5 (the case is the escalation surface). This adds a `CaseStatus` enum and a single `set_case_status(item_id, status)` op (covers both transitions); it is a no-op when the item has no case (dedup closes create none). On Elastic this maps to the Cases API status `open|in-progress|closed`.

_Alternative — close every case including escalations:_ rejected; it would drop true positives off the human's active queue, defeating escalation-via-case. _Alternative — a dedicated `close_case()` method:_ rejected in favor of the more general `set_case_status`, which also expresses the in-progress transition.

### D8 — Review-once is the platform's job; the loop opts out of DB dedup
The orchestrator's DB-based dedup (`find_by_key` → return existing, skip analyst) duplicated a guarantee the platform already provides — `fetch_open` only returns `OPEN` items and `acknowledge` removes them, so a triaged alert is never re-surfaced (D2, and the existing "platform is the triage state store" principle). Two sources of truth caused confusion. `handle` now takes `dedup: bool = True`: the `/investigate` API keeps review-once (default), while `run_once` passes `dedup=False` — the analyst always runs and the investigation is **upserted** by key (existing record's id reused, updated in place). The investigations store becomes pure context (for lookups/MCP), not a triage gate.

_Consequence:_ two different alert IDs for the same underlying event each get a full triage + separate case (the DB no longer collapses them) — acceptable, since review-once is per-alert-firing at the platform. _Alternative — remove dedup everywhere:_ rejected; the direct `/investigate` API has no platform behind it, so its idempotency (and token-cost guard on repeat submits) is worth keeping.

### D6 — Elastic mapping
`acknowledge` → signals status `acknowledged`. `set_status(CLOSED, reason)` → signals status `closed` plus the close reason attached via the Elastic mechanism confirmed by the spike (workflow tags / `workflow_reason` field, or the case). The old `ESCALATED → acknowledged` mapping is removed. `InMemoryTriagePlatform` records `(status, reason)` in memory for dev/tests.

## Risks / Trade-offs

- **[True positives are auto-closed]** → A real threat closed with reason `TRUE_POSITIVE` could be missed if operators only watch the alert queue. Mitigation: case-always + high severity + `benny:escalate` tag; operators triage the case queue. Confirm this matches SOC workflow before rollout (Open Questions).
- **[Elastic close-reason API unknown]** → The precise field/endpoint to persist a close reason on an Elastic alert isn't confirmed. Mitigation: spike against the target cluster; degrade gracefully to close-without-reason + the reason in the case comment if the field is unavailable.
- **[Ack then crash]** → If the process dies after `acknowledge` but before close, the alert is stuck `ACKNOWLEDGED` (not re-fetched, not resolved). Mitigation: acceptable for now (visible in the acknowledged queue); a future sweep could re-open stale acknowledged items past a TTL.
- **[Breaking contract]** → Both platforms and their contract tests must be updated in lockstep. Mitigation: the shared helper + `runtime_checkable` Protocol make the gap a test failure, not a silent drift.

## Migration Plan

1. Extend `base.py`: add `TriageStatus.ACKNOWLEDGED`, `CloseReason`, `acknowledge(item_id)`, and the `set_status(..., reason=None)` signature; remove `ESCALATED`.
2. Implement `acknowledge` + reason handling in `memory.py` and `elastic.py` (Elastic reason mechanism gated on the spike).
3. Refactor `loop.py`: extract the shared per-item helper, insert `acknowledge` before `handle`, map disposition → reason, apply D3 edge cases; slim `run_once`.
4. Update `triage-platform` + `elastic-triage-platform` specs and contract tests.
5. Rollback: revert the change set; no persisted schema migration, so rollback is code-only (already-closed alerts stay closed).

## Open Questions

- **True-positive terminal state** — close-with-reason `TRUE_POSITIVE` (this design) vs. leave `ACKNOWLEDGED` for a human. Leaning close-with-reason per the agreed flow; needs a final nod against real SOC practice.
- **Elastic close-reason field** — _Resolved (spike):_ the detection-engine signals status API (`POST /api/detection_engine/signals/status`) takes only `{signal_ids, status}` — no portable close-reason field across Elastic 8.x. Persisting `kibana.alert.workflow_reason`/`workflow_tags` directly is version-dependent and not exposed by that endpoint. **Decision:** set the alert to `closed` via signals status, and record the human-readable reason on the **case** (a comment via the Cases API we already use) whenever a case exists. Dedup closes have no case, so their `DUPLICATE` reason lives in the triage log only. Revisit if the target cluster exposes a stable workflow-reason write path.
- **Stale `ACKNOWLEDGED` recovery** — do we need a TTL sweep to re-open alerts acknowledged but never closed (crash mid-triage)? Deferred unless it bites.
