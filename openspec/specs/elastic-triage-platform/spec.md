# elastic-triage-platform Specification

## Purpose
TBD - created by archiving change elastic-triage-platform. Update Purpose after archive.
## Requirements
### Requirement: ElasticSecurityPlatform implements TriagePlatform
The system SHALL provide `ElasticSecurityPlatform` under `src/platforms/` implementing the `TriagePlatform` Protocol against Elastic Security via the **Kibana API** — all operations (alerts search, signals status, cases) over a single Kibana HTTP client. It SHALL NOT use the Elasticsearch client; that is the `DataAgent`'s surface. Callers interact only through the `TriagePlatform` interface.

#### Scenario: Satisfies the contract
- **WHEN** `ElasticSecurityPlatform` is checked against `TriagePlatform`
- **THEN** all six operations (`fetch_open`, `get`, `comment`, `set_severity`, `set_status`, `create_case`) are present and callable

---

### Requirement: fetch_open returns open detection alerts
`fetch_open(limit)` SHALL query the Kibana detection-engine signals search API (`POST /api/detection_engine/signals/search`) for documents with `kibana.alert.workflow_status: open`, most recent first, bounded by `limit`, and return them as raw dicts each carrying an `id` (the alert `_id`). `get(item_id)` SHALL return a single alert document or `None`.

#### Scenario: Only open alerts are returned
- **WHEN** `fetch_open` runs against an index containing open and closed alerts
- **THEN** only alerts with `workflow_status: open` are returned, each with an `id`

---

### Requirement: set_status drives Elastic workflow status
`set_status` SHALL update the alert's workflow status via the detection-engine signals status API: `TriageStatus.CLOSED` → Elastic `closed`, `TriageStatus.ESCALATED` → Elastic `acknowledged`. Because `fetch_open` filters on `open`, a triaged alert (closed or acknowledged) SHALL NOT be returned again — Benny holds no triage cursor of its own.

#### Scenario: Benign alert is closed in Elastic
- **WHEN** `set_status(item_id, CLOSED)` is called
- **THEN** the signals status API is called to set that alert's status to `closed`

#### Scenario: Escalated alert is acknowledged in Elastic
- **WHEN** `set_status(item_id, ESCALATED)` is called
- **THEN** the signals status API is called to set that alert's status to `acknowledged`

---

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

