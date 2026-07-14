# investigation-idempotency Specification

## Purpose
TBD - created by archiving change investigation-idempotency. Update Purpose after archive.
## Requirements
### Requirement: Modules supply a dedup key
The `AnalystModule` contract SHALL include `dedup_key(inp) -> str`, a stable identity for an input. The SIEM module SHALL key on `alert.id` — one investigation per alert firing; a recurrence arrives as a new `alert.id` and is a new investigation.

#### Scenario: SIEM dedup key is the alert id
- **WHEN** `dedup_key` is called with an alert
- **THEN** it returns the alert's `id`

---

### Requirement: Each finding is reviewed once
The `OrchestratorAgent` SHALL namespace the dedup key as `<module>:<module dedup key>` and, before running, look up an existing investigation for that key. If one exists it SHALL return it without re-running the analyst; otherwise it SHALL run the analyst, tag the investigation with `key` and `module`, persist it, and return it as newly created.

#### Scenario: Duplicate returns existing without re-running
- **WHEN** `handle` is called for a request whose dedup key already has a stored investigation
- **THEN** the stored investigation is returned, the analyst is not run, and nothing new is persisted

#### Scenario: Fresh request runs and persists
- **WHEN** `handle` is called for a request with no existing investigation for its key
- **THEN** the analyst runs, the investigation is tagged with `key` and `module`, persisted, and returned as created

---

### Requirement: Investigation carries dedup key and module
`Investigation` SHALL include `key: str` and `module: str` fields identifying the dedup key and the producing module. Both default to empty and are set by the orchestrator on a fresh run.

#### Scenario: Persisted investigation is tagged
- **WHEN** a fresh investigation is persisted
- **THEN** its `key` is `<module>:<dedup key>` and its `module` is the module name

---

### Requirement: POST /investigate is idempotent
`POST /investigate` SHALL return `202` for a freshly-run investigation and `200` when returning an existing one for a repeated alert. Submitting the same alert twice SHALL yield a single stored investigation.

#### Scenario: Repeat submission returns existing with 200
- **WHEN** the same alert is submitted twice
- **THEN** the first response is `202` and the second is `200` with the same investigation id, and only one investigation is stored

---

### Requirement: Dedup lookup by key
`InvestigationModel` SHALL provide `find_by_key(key) -> Investigation | None` returning the stored investigation with the given dedup key, or `None`.

#### Scenario: find_by_key returns match or None
- **WHEN** an investigation with a given key is stored
- **THEN** `find_by_key(key)` returns it, and returns `None` for an unknown key

