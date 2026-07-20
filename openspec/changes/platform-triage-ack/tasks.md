## 1. Contract & state model (`base.py`)

- [x] 1.1 Add `TriageStatus.ACKNOWLEDGED`; remove `TriageStatus.ESCALATED` (escalation moves to the case, per design D2/D5)
- [x] 1.2 Add a `CloseReason` enum: `DUPLICATE`, `FALSE_POSITIVE`, `BENIGN_POSITIVE`, `TRUE_POSITIVE`, `OTHER`, `NONE`
- [x] 1.3 Add `acknowledge(item_id)` to the `TriagePlatform` Protocol (docstring: OPEN → ACKNOWLEDGED, removes item from the open queue)
- [x] 1.4 Extend `set_status` signature to `set_status(item_id, status, reason: CloseReason | None = None)` and document that a `CLOSED` status carries a reason

## 2. Elastic close-reason spike (design Open Question)

- [x] 2.1 Confirm against the target cluster how to persist a close reason on an Elastic alert (signals status `workflow_reason` / workflow tags vs. case-only); record the finding in `design.md`
- [x] 2.2 Decide the fallback path if no native field exists (close-without-reason + reason in the case comment)

## 3. Platform implementations

- [x] 3.1 `memory.py`: implement `acknowledge` (OPEN → ACKNOWLEDGED), exclude ACKNOWLEDGED from `fetch_open`, record `(status, reason)`, and update `set_status` for the new signature
- [x] 3.2 `elastic.py`: implement `acknowledge` → signals status `acknowledged`; remove `_STATUS_MAP` `ESCALATED → acknowledged`; map `set_status(CLOSED, reason)` → `closed` + persist reason per the 2.1 finding
- [x] 3.3 `elastic.py`: ensure `fetch_open` (filter `workflow_status: open`) still excludes acknowledged/closed alerts

## 4. Triage-loop refactor (`loop.py`)

- [x] 4.1 Add a disposition → `CloseReason` mapper (replace `_BENIGN_DISPOSITIONS`) per the design D4 table
- [x] 4.2 Extract a single shared write-back helper: create_case → comment → set_severity → `set_status(CLOSED, reason)`
- [x] 4.3 In each iteration, call `acknowledge(item_id)` before `handle`
- [x] 4.4 Dedup hit (`not result.created`): close with `DUPLICATE`, no case/comment/severity
- [x] 4.5 No investigation (`result.investigation is None`): leave `ACKNOWLEDGED` and log; create no case
- [x] 4.6 True-positive: create case with severity from `outcome.priority`, then close with `TRUE_POSITIVE` (escalation via the case, not alert status)
- [x] 4.7 Slim `run_once` to a thin fetch + loop delegating to the shared helper

## 5. Tests

- [x] 5.1 `test_memory.py`: replace ESCALATED assertions; cover `acknowledge` claims + drops from `fetch_open`, and close-with-reason recording
- [x] 5.2 `test_elastic.py`: replace ESCALATED mapping test; assert `acknowledge` → `acknowledged` and `set_status(CLOSED, reason)` → `closed` (+ reason persistence / fallback)
- [x] 5.3 `test_loop.py`: assert acknowledge-before-handle ordering; benign→FALSE_POSITIVE/BENIGN_POSITIVE close; true-positive→TRUE_POSITIVE close + case severity; dedup→DUPLICATE close (no re-write); unresolved→left ACKNOWLEDGED
- [x] 5.4 Contract test: `runtime_checkable` check includes `acknowledge` for both platforms

## 6. Spec sync & validation

- [x] 6.1 Run `openspec validate platform-triage-ack --strict`
- [x] 6.2 Run the full test suite and confirm green
- [ ] 6.3 On archive, sync `triage-platform` + `elastic-triage-platform` deltas into `openspec/specs/`

## 7. Case lifecycle (open → in-progress → closed)

- [x] 7.1 Add `CaseStatus` enum + `set_case_status(item_id, status)` to the `TriagePlatform` Protocol (`base.py`)
- [x] 7.2 `memory.py`: track case status (OPEN on create), `set_case_status` (no-op without a case), `case_status_of` inspector
- [x] 7.3 `elastic.py`: `set_case_status` → Cases API `PATCH` (`open|in-progress|closed`), version refresh, 406-tolerant, no-op without a case
- [x] 7.4 `loop.py`: move case to `IN_PROGRESS` after create; on resolve (`FALSE_POSITIVE`/`BENIGN_POSITIVE`) close the case; leave `IN_PROGRESS` on escalation
- [x] 7.5 Tests: memory lifecycle + no-op; loop benign→case CLOSED / true-positive→case IN_PROGRESS; elastic PATCH status + no-op; contract includes `set_case_status`
- [x] 7.6 Fix stale case-version 409: `_attach_alert` refreshes the cached version after attach (regression test) so the subsequent `set_case_status` PATCH doesn't 409

## 8. Loop opts out of DB dedup (platform owns review-once)

- [x] 8.1 `orchestrator.handle` gains `dedup: bool = True`; with `dedup=False` always run the analyst and upsert by key (reuse existing record id); `created = existing is None`
- [x] 8.2 `loop.run_once` calls `handle(dedup=False)` and writes back every produced investigation (remove the dedup→`DUPLICATE` branch); unresolved → left `ACKNOWLEDGED`
- [x] 8.3 Tests: orchestrator dedup=False re-runs+upserts / fresh creates; loop passes dedup=False and writes back regardless of `created`; API idempotency (dedup default) unchanged
- [x] 8.4 Specs: rework `triage-platform` idempotency + close-reason (drop dedup→DUPLICATE); add `investigation-idempotency` delta (dedup flag + upsert)
