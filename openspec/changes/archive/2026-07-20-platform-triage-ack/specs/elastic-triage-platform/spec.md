## ADDED Requirements

### Requirement: acknowledge marks an Elastic alert in-progress
`acknowledge(item_id)` SHALL set the alert's Elastic workflow status to `acknowledged` via the detection-engine signals status API (`POST /api/detection_engine/signals/status`), signalling that Benny is working the alert. Because `fetch_open` filters on `open`, an acknowledged alert SHALL NOT be returned again during its investigation.

#### Scenario: Alert is acknowledged in Elastic
- **WHEN** `acknowledge(item_id)` is called
- **THEN** the signals status API is called to set that alert's status to `acknowledged`, and `fetch_open` no longer returns it

### Requirement: set_case_status drives the Kibana case lifecycle
`set_case_status(item_id, status)` SHALL update the alert's Kibana case status via the Cases API (`PATCH /api/cases`) to Elastic's `open | in-progress | closed`, using the case's tracked version and refreshing it from the response. It SHALL be a no-op when no case exists for the item, and SHALL tolerate a no-op `406` (status already at target) without raising.

#### Scenario: Case is moved to in-progress then closed
- **WHEN** `set_case_status(item_id, IN_PROGRESS)` then `set_case_status(item_id, CLOSED)` are called for an item with a case
- **THEN** the Cases API is PATCHed with status `in-progress`, then `closed`

#### Scenario: No case to move
- **WHEN** `set_case_status(item_id, CLOSED)` is called for an item with no created case
- **THEN** no Cases API call is made and no error is raised

## MODIFIED Requirements

### Requirement: ElasticSecurityPlatform implements TriagePlatform
The system SHALL provide `ElasticSecurityPlatform` under `src/adapters/platforms/` implementing the `TriagePlatform` Protocol against Elastic Security via the **Kibana API** — all operations (alerts search, signals status, cases) over a single Kibana HTTP client. It SHALL NOT use the Elasticsearch client; that is the `DataAgent`'s surface. Callers interact only through the `TriagePlatform` interface.

#### Scenario: Satisfies the contract
- **WHEN** `ElasticSecurityPlatform` is checked against `TriagePlatform`
- **THEN** all operations (`fetch_open`, `get`, `acknowledge`, `comment`, `set_severity`, `set_status`, `create_case`, `set_case_status`) are present and callable

### Requirement: set_status drives Elastic workflow status
`acknowledge` and `set_status` SHALL update the alert's workflow status via the detection-engine signals status API: `acknowledge(item_id)` → Elastic `acknowledged` ("in progress"); `set_status(item_id, CLOSED, reason)` → Elastic `closed`, persisting the `CloseReason` via the confirmed Elastic mechanism (workflow tags / reason field), degrading to close-without-reason plus the reason in the case comment if that field is unavailable. Because `fetch_open` filters on `open`, an acknowledged or closed alert SHALL NOT be returned again — Benny holds no triage cursor of its own. The previous `ESCALATED → acknowledged` mapping is removed; escalation is conveyed by the case, not the alert status.

#### Scenario: Alert is closed with a reason in Elastic
- **WHEN** `set_status(item_id, CLOSED, reason=CloseReason.FALSE_POSITIVE)` is called
- **THEN** the signals status API sets that alert's status to `closed` and the close reason is persisted (or recorded in the case comment as a fallback)

#### Scenario: A true positive is closed and escalated via the case
- **WHEN** an investigation returns a true-positive disposition and `set_status(item_id, CLOSED, reason=CloseReason.TRUE_POSITIVE)` is called after the case is created with severity set from `outcome.priority`
- **THEN** the alert is set to `closed` with reason `TRUE_POSITIVE` and the escalation is durable on the case (severity), not on the alert queue
