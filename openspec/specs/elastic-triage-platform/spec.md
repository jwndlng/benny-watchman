# elastic-triage-platform Specification

## Purpose
TBD - created by archiving change elastic-triage-platform. Update Purpose after archive.
## Requirements
### Requirement: ElasticSecurityPlatform implements TriagePlatform
The system SHALL provide `ElasticSecurityPlatform` under `src/adapters/platforms/` implementing the `TriagePlatform` Protocol against Elastic Security via the **Kibana API** — all operations (alerts search, signals status, cases) over a single Kibana HTTP client. It SHALL NOT use the Elasticsearch client; that is the `DataAgent`'s surface. Callers interact only through the `TriagePlatform` interface.

#### Scenario: Satisfies the contract
- **WHEN** `ElasticSecurityPlatform` is checked against `TriagePlatform`
- **THEN** all operations (`fetch_open`, `get`, `acknowledge`, `comment`, `set_severity`, `set_status`, `create_case`, `set_case_status`) are present and callable

### Requirement: fetch_open returns open detection alerts
`fetch_open(limit)` SHALL query the Kibana detection-engine signals search API (`POST /api/detection_engine/signals/search`) for documents with `kibana.alert.workflow_status: open`, most recent first, bounded by `limit`, and return them as raw dicts each carrying an `id` (the alert `_id`). `get(item_id)` SHALL return a single alert document or `None`.

#### Scenario: Only open alerts are returned
- **WHEN** `fetch_open` runs against an index containing open and closed alerts
- **THEN** only alerts with `workflow_status: open` are returned, each with an `id`

---

### Requirement: set_status drives Elastic workflow status
`acknowledge` and `set_status` SHALL update the alert's workflow status via the detection-engine signals status API: `acknowledge(item_id)` → Elastic `acknowledged` ("in progress"); `set_status(item_id, CLOSED, reason)` → Elastic `closed`, persisting the `CloseReason` via the confirmed Elastic mechanism (workflow tags / reason field), degrading to close-without-reason plus the reason in the case comment if that field is unavailable. Because `fetch_open` filters on `open`, an acknowledged or closed alert SHALL NOT be returned again — Benny holds no triage cursor of its own. The previous `ESCALATED → acknowledged` mapping is removed; escalation is conveyed by the case, not the alert status.

#### Scenario: Alert is closed with a reason in Elastic
- **WHEN** `set_status(item_id, CLOSED, reason=CloseReason.FALSE_POSITIVE)` is called
- **THEN** the signals status API sets that alert's status to `closed` and the close reason is persisted (or recorded in the case comment as a fallback)

#### Scenario: A true positive is closed and escalated via the case
- **WHEN** an investigation returns a true-positive disposition and `set_status(item_id, CLOSED, reason=CloseReason.TRUE_POSITIVE)` is called after the case is created with severity set from `outcome.priority`
- **THEN** the alert is set to `closed` with reason `TRUE_POSITIVE` and the escalation is durable on the case (severity), not on the alert queue

### Requirement: Write-back uses Kibana Cases; severity is case-level
`create_case` SHALL open a Kibana case (owner `securitySolution`), attach the alert, and return the case id; the platform SHALL retain the `item_id → case_id` mapping for the run. `comment` SHALL add a comment to that case. `set_severity` SHALL set the **case** severity (normalized to Elastic's `low|medium|high|critical`) — alert severity is rule-derived and not modified.

#### Scenario: Case created, commented, and severity set
- **WHEN** `create_case(item_id, investigation)` then `comment(item_id, text)` then `set_severity(item_id, "high")` are called
- **THEN** a case is created via the Cases API and its id retained, a comment is posted to that case, and the case severity is set to `high`

#### Scenario: Comment/severity before a case exists
- **WHEN** `comment` or `set_severity` is called for an `item_id` with no created case
- **THEN** the platform raises or no-ops predictably (documented), rather than writing to an unrelated resource

---

### Requirement: Elastic alerts map to the SIEM Alert schema
The platform SHALL map an Elastic alert document to the SIEM `Alert`: `id`←`_id`, `type`←`kibana.alert.rule.name`, `title`←`kibana.alert.rule.name`, `description`←`kibana.alert.reason`, `severity`←`kibana.alert.severity`, `source`←`"elastic"`, `timestamp`←`@timestamp`, `raw`←the full document, and `guidance`←the rule investigation note (see below). The `type` mapping is plain metadata and dedup input — it no longer selects a runbook.

#### Scenario: An alert document becomes a valid Alert payload
- **WHEN** an Elastic alert document is fetched and mapped
- **THEN** the resulting payload validates as an `Alert`, its `type` reflects the rule name as metadata, and `guidance` is populated when the rule has an investigation note

---

### Requirement: Investigation guidance is sourced from the detection rule note
The platform SHALL populate `Alert.guidance` from the detection rule's investigation note with `source` = `"elastic-rule-note"`. It SHALL read the note from the alert document when present and otherwise fetch the rule once, caching the note per rule uuid so cost is per unique rule, not per alert. When the rule has no note, `guidance` SHALL be `None`.

#### Scenario: Rule note becomes guidance
- **WHEN** an alert's detection rule has an investigation note
- **THEN** the mapped `Alert.guidance.text` is the note and `guidance.source` is `"elastic-rule-note"`

#### Scenario: Note resolution is cached per rule
- **WHEN** multiple open alerts share the same detection rule
- **THEN** the rule note is resolved once and reused for all of them

#### Scenario: No note yields no guidance
- **WHEN** an alert's detection rule has no investigation note
- **THEN** the mapped `Alert.guidance` is `None`

---

### Requirement: Platform is selected by configuration
The composition root SHALL build `ElasticSecurityPlatform` when Kibana triage settings are present in configuration (the `[kibana]` section — `url` and `case_owner`, with the API key sourced from its environment alias), and fall back to `InMemoryTriagePlatform` otherwise. Credentials SHALL be scoped to alerts read + signal-status write + cases — never remediation.

#### Scenario: Elastic selected when configured
- **WHEN** the app starts with the `[kibana]` section and its API key present
- **THEN** `run_once` operates against `ElasticSecurityPlatform`

#### Scenario: In-memory fallback when unconfigured
- **WHEN** the app starts without Kibana triage settings
- **THEN** the in-memory platform is used and no Elastic calls are made

---

### Requirement: Kibana configuration may target a non-default space
The Kibana base URL MAY include a Kibana space prefix (`/s/<space-id>`); all Kibana API calls SHALL then operate within that space. When no space prefix is present, calls operate in the default space.

#### Scenario: Space prefix scopes API calls
- **WHEN** the Kibana `url` is configured as `https://host/s/isec`
- **THEN** signals search, signal-status, and cases calls are issued under the `/s/isec` prefix

#### Scenario: No prefix uses the default space
- **WHEN** the Kibana `url` has no `/s/<space-id>` segment
- **THEN** calls operate in the default Kibana space

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

