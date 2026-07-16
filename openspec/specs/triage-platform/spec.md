# triage-platform Specification

## Purpose
TBD - created by archiving change triage-platform. Update Purpose after archive.
## Requirements
### Requirement: TriagePlatform defines the operational I/O contract
The system SHALL provide a `TriagePlatform` Protocol under `src/platforms/` with intake, tracking, and write-back operations: `fetch_open(limit)`, `get(item_id)`, `comment(item_id, text)`, `set_severity(item_id, severity)`, `set_status(item_id, status)`, and `create_case(item_id, investigation) -> case_id`. Intake work items SHALL be raw payloads (dicts carrying an `id`), so the platform stays decoupled from module input schemas.

#### Scenario: In-memory platform satisfies the contract
- **WHEN** `InMemoryTriagePlatform` is checked against `TriagePlatform`
- **THEN** all six operations are present and callable, and `fetch_open` returns raw dict work items each having an `id`

---

### Requirement: The platform is the triage state store
`fetch_open` SHALL return only work items still needing triage (status `OPEN`). Once a terminal status (`CLOSED` or `ESCALATED`) is set on an item, it SHALL NOT be returned by `fetch_open` again. Benny SHALL hold no external cursor or triage state of its own.

#### Scenario: Triaged items drop out of the open queue
- **WHEN** an item is fetched, then `set_status(item_id, CLOSED)` (or `ESCALATED`) is called
- **THEN** a subsequent `fetch_open` no longer includes that item

---

### Requirement: The triage-loop investigates and writes back
The system SHALL provide `run_once(orchestrator, platform, hint)` that, for each open work item, calls `OrchestratorAgent.handle(raw, hint)` and, for a freshly-created investigation, writes the outcome back to the platform: **always** create a case, add a comment, set severity from `outcome.priority`, and set a terminal status — `CLOSED` when the disposition is benign/false-positive, `ESCALATED` otherwise. The loop SHALL be domain-agnostic (drive only via `handle` and the generic `outcome`).

#### Scenario: Benign alert is auto-closed with a case
- **WHEN** `run_once` processes an open item whose investigation returns a benign/false-positive disposition
- **THEN** a case is created, a comment and severity are written, and the item's status is set to `CLOSED`

#### Scenario: True-positive is escalated with a case
- **WHEN** `run_once` processes an open item whose investigation returns a true-positive/actionable disposition
- **THEN** a case is created, a comment and severity are written, and the item's status is set to `ESCALATED`

---

### Requirement: Write-back is idempotent per work item
`run_once` SHALL write back only when `handle` reports a freshly-created investigation. When investigation is deduplicated (already triaged) or no module resolves the item, the loop SHALL NOT create a case, comment, or change status for it.

#### Scenario: Re-seen item is not re-written
- **WHEN** `run_once` encounters an item whose investigation already exists (dedup hit)
- **THEN** no new case, comment, or status change is produced for that item

#### Scenario: Unresolved item is skipped
- **WHEN** an open item cannot be handled by any module (`handle` returns no investigation)
- **THEN** the loop skips it without creating a case or changing its status

---

### Requirement: The platform layer does not couple to core
Code under `src/platforms/` MAY import from `src/core/` and `src/schemas/`, but `src/core/` SHALL NOT import from `src/platforms/`. The triage-loop lives in `src/platforms/` so that core remains unaware of the platform layer.

#### Scenario: Dependency direction holds
- **WHEN** the import graph is inspected
- **THEN** no module under `src/core/` imports from `src/platforms/`

