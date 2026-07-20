## Why

`run_once` never signals that Benny has started working an alert. It fetches OPEN items, runs the full (slow, LLM-bound) investigation, and only writes status back at the very end. During that whole window the alert stays OPEN, so a concurrent or repeat pass can re-fetch and re-investigate the same item, and there is no operator-visible trail that "someone is on it." The terminal write is also a coarse `CLOSED`/`ESCALATED` binary that throws away *why* the analyst reached its disposition.

## What Changes

- **Acknowledge on start** — add an `acknowledge(item_id)` primitive to the `TriagePlatform` Protocol. The triage-loop calls it *before* investigating each alert, taking it out of the open queue and marking "Benny is on it." (Elastic: `open → acknowledged`.)
- **Close with a reason** — replace the `CLOSED`/`ESCALATED` terminal binary with a close-with-reason terminal write derived from the investigation's disposition (Duplicate, False Positive, Benign positive, True positive, Other, or none). The universal per-item flow becomes: **acknowledge → investigate → create case + move to in-progress + comment + severity → close with reason.**
- **Case lifecycle mirrors the work** — the case Benny opens is moved to **in-progress** while triaging, then **closed** when he resolves it (benign); an escalated (true-positive) case is left **in-progress** for a human. Adds `set_case_status` + a `CaseStatus` enum to the platform contract.
- **Loop opts out of DB dedup** — review-once is the platform's job (`fetch_open` + `acknowledge`), so the triage loop calls `handle(dedup=False)` and writes back every produced investigation; the investigations DB is upserted purely for context/MCP, not used as a triage gate. `handle` gains a `dedup` flag (default `True`, so the `/investigate` API stays idempotent).
- **Thin `run_once`, one shared helper** — keep the write-back sequence in a single shared function in `loop.py` that every platform reuses; `run_once` becomes a thin fetch + loop. Only the new `acknowledge` primitive is added to the Protocol — platforms do **not** each reimplement the case/comment/close sequence.
- **BREAKING (contract):** `TriagePlatform` gains `acknowledge(item_id)`, so `InMemoryTriagePlatform` and `ElasticSecurityPlatform` must implement it. The terminal-status model changes from `set_status(CLOSED|ESCALATED)` to close-with-reason.

## Capabilities

### New Capabilities

_(none — this refines existing triage behavior rather than introducing a new capability)_

### Modified Capabilities

- `triage-platform`: adds the `acknowledge` primitive to the contract; the triage-loop acknowledges before investigating and writes a close-with-reason terminal state instead of the `CLOSED`/`ESCALATED` binary; write-back stays idempotent (fresh investigations only) and domain-agnostic (driven via `handle` + generic `outcome`).
- `elastic-triage-platform`: implements `acknowledge` (signals status → `acknowledged`) and maps dispositions to Elastic close reasons; revisits the `set_status` mapping now that `acknowledged` means "in progress / on it," not "escalated."
- `investigation-idempotency`: `handle` gains a `dedup` flag (default `True` — API unchanged); with `dedup=False` the analyst always runs and the record is upserted by key. Review-once for the triage loop moves to the platform.

## Impact

- **Code:** `src/adapters/platforms/base.py` (Protocol + status/reason model), `src/adapters/platforms/loop.py` (`run_once` + shared write-back helper), `src/adapters/platforms/memory.py` and `src/adapters/platforms/elastic.py` (implement `acknowledge`, close-with-reason).
- **Behavior:** an in-flight alert is claimed immediately, so it can't be picked up twice within a run. True-positive handling changes — escalation is conveyed via the case (severity/tags) while the alert is closed with a `true_positive` reason, rather than left `acknowledged`/open indefinitely. _(Open design question: confirm whether true positives close-with-reason or stay `acknowledged` for a human — resolved in `design.md`.)_
- **Elastic API:** the exact close-reason mechanism (signals status vs. workflow tags / `workflow_reason` vs. case field) must be confirmed against the target cluster — extends the existing Elastic spike note.
- **Specs/tests:** update `triage-platform` and `elastic-triage-platform` scenarios; platform contract tests must cover `acknowledge` and close-with-reason.
