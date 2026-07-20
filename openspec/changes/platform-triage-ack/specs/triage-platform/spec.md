## ADDED Requirements

### Requirement: Acknowledge claims a work item before investigation
The `TriagePlatform` SHALL provide `acknowledge(item_id)` that transitions a work item from `OPEN` to `ACKNOWLEDGED`, signalling that Benny has started working it. Acknowledgement SHALL remove the item from the open queue so it is not re-fetched by a concurrent or subsequent pass while its investigation is in flight.

#### Scenario: Acknowledged item is claimed
- **WHEN** `acknowledge(item_id)` is called on an `OPEN` item
- **THEN** its status becomes `ACKNOWLEDGED` and a subsequent `fetch_open` no longer returns it

### Requirement: Terminal close carries a disposition-derived reason
The system SHALL define a `CloseReason` enum (`DUPLICATE`, `FALSE_POSITIVE`, `BENIGN_POSITIVE`, `TRUE_POSITIVE`, `OTHER`, `NONE`) and map `outcome.disposition` onto it: `false_positive` → `FALSE_POSITIVE`; `benign` / `not_exploitable` → `BENIGN_POSITIVE`; `true_positive` / `exploitable` → `TRUE_POSITIVE`; `inconclusive` or unknown → `OTHER`; an absent disposition → `NONE`. (`DUPLICATE` remains a valid close reason but is not auto-assigned by the loop.) Closing a work item SHALL record its reason.

#### Scenario: Disposition maps to a close reason
- **WHEN** an investigation completes with disposition `true_positive`
- **THEN** the item is closed with reason `TRUE_POSITIVE`

#### Scenario: Unknown disposition closes as OTHER
- **WHEN** an investigation completes with disposition `inconclusive`
- **THEN** the item is closed with reason `OTHER`

## MODIFIED Requirements

### Requirement: TriagePlatform defines the operational I/O contract
The system SHALL provide a `TriagePlatform` Protocol under `src/adapters/platforms/` with intake, tracking, and write-back operations: `fetch_open(limit)`, `get(item_id)`, `acknowledge(item_id)`, `comment(item_id, text)`, `set_severity(item_id, severity)`, `set_status(item_id, status, reason=None)`, `create_case(item_id, investigation) -> case_id`, and `set_case_status(item_id, status)`. `acknowledge` SHALL move an item from `OPEN` to `ACKNOWLEDGED`; a terminal `set_status(item_id, CLOSED, reason)` SHALL carry a `CloseReason`; `set_case_status` SHALL move the item's case through its lifecycle (`CaseStatus.OPEN | IN_PROGRESS | CLOSED`) and SHALL be a no-op when no case exists for the item. Intake work items SHALL be raw payloads (dicts carrying an `id`), so the platform stays decoupled from module input schemas.

#### Scenario: In-memory platform satisfies the contract
- **WHEN** `InMemoryTriagePlatform` is checked against `TriagePlatform`
- **THEN** all operations — including `acknowledge` — are present and callable, and `fetch_open` returns raw dict work items each having an `id`

#### Scenario: Close records a reason
- **WHEN** `set_status(item_id, CLOSED, reason=CloseReason.FALSE_POSITIVE)` is called
- **THEN** the item is recorded as `CLOSED` with reason `FALSE_POSITIVE`

### Requirement: The platform is the triage state store
`fetch_open` SHALL return only work items still needing triage (status `OPEN`). Once an item is `ACKNOWLEDGED` (claimed) or `CLOSED` (terminal), it SHALL NOT be returned by `fetch_open` again. Benny SHALL hold no external cursor or triage state of its own.

#### Scenario: Acknowledged items drop out of the open queue
- **WHEN** an item is fetched and `acknowledge(item_id)` is called
- **THEN** a subsequent `fetch_open` no longer includes that item

#### Scenario: Closed items stay out of the open queue
- **WHEN** `set_status(item_id, CLOSED, reason)` is called
- **THEN** a subsequent `fetch_open` no longer includes that item

### Requirement: The triage-loop investigates and writes back
The system SHALL provide `run_once(orchestrator, platform, hint)` that, for each open work item, **acknowledges it before investigating**, calls `OrchestratorAgent.handle(raw, hint, dedup=False)`, and — for **any produced investigation** — writes the outcome back through a **single shared write-back helper**: create a case, move the case to `IN_PROGRESS`, add a comment, set case severity from `outcome.priority`, and **close the item with a `CloseReason` derived from the disposition**. When Benny resolves the item (benign — `FALSE_POSITIVE`/`BENIGN_POSITIVE`), the helper SHALL also close the case (`CaseStatus.CLOSED`). A `TRUE_POSITIVE` close SHALL escalate via the case — severity from `outcome.priority` and the case **left `IN_PROGRESS` for a human** — not by leaving the alert open. `run_once` SHALL remain a thin fetch + loop with the write-back sequence in one shared helper reused across platforms. The loop SHALL be domain-agnostic (drive only via `handle` and the generic `outcome`).

#### Scenario: Alert is acknowledged before investigation
- **WHEN** `run_once` begins processing an open item
- **THEN** `acknowledge(item_id)` is called before `handle` runs

#### Scenario: Benign alert is closed and its case is closed
- **WHEN** `run_once` processes an open item whose investigation returns a benign/false-positive disposition
- **THEN** a case is created and moved to `IN_PROGRESS`, a comment and severity are written, the item is closed with reason `FALSE_POSITIVE` or `BENIGN_POSITIVE`, and the case is moved to `CLOSED`

#### Scenario: True-positive is escalated with the case left in progress
- **WHEN** `run_once` processes an open item whose investigation returns a true-positive/actionable disposition
- **THEN** a case is created with case severity from `outcome.priority`, the item is closed with reason `TRUE_POSITIVE`, and the case is left `IN_PROGRESS` for a human

### Requirement: The case tracks Benny's triage lifecycle
The case Benny opens SHALL follow his work: opened on creation, moved to `IN_PROGRESS` while triaging, and moved to `CLOSED` once he resolves the finding. An **escalated** case (true-positive) SHALL be left `IN_PROGRESS` so it remains on a human's active queue. `set_case_status` SHALL be a no-op when the item has no case.

#### Scenario: Case is moved to in-progress while triaging
- **WHEN** the shared write-back creates a case for a fresh investigation
- **THEN** the case is moved to `IN_PROGRESS` before the item is closed

#### Scenario: set_case_status is a no-op without a case
- **WHEN** `set_case_status(item_id, CLOSED)` is called for an item that has no case
- **THEN** no case-status change is attempted and no error is raised

### Requirement: Write-back is idempotent per work item
Review-once SHALL be the platform's responsibility, not a Benny-side store: `run_once` SHALL call `handle` with `dedup=False` and write back **every** produced investigation, relying on the platform's `fetch_open` + `acknowledge` to prevent a triaged item from being re-surfaced. The investigations store SHALL be upserted for context/lookups (updating any existing record for the key), never used as a triage gate in the loop. When no module resolves the item (`handle` returns no investigation), the loop SHALL leave the item `ACKNOWLEDGED` for a human and SHALL NOT create a case.

#### Scenario: Every produced investigation is written back
- **WHEN** `run_once` processes an open item that yields an investigation (regardless of whether its record was new or updated)
- **THEN** a case is created and the item is closed with a disposition-derived reason

#### Scenario: Unresolved item is left acknowledged
- **WHEN** an open item cannot be handled by any module (`handle` returns no investigation)
- **THEN** the loop creates no case and leaves the item `ACKNOWLEDGED`
