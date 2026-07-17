## ADDED Requirements

### Requirement: Work items carry structured investigation guidance
The system SHALL define an `InvestigationGuidance` type with `text: str` (the guidance body), `source: str` (provenance, e.g. `"submitter"` or `"elastic-rule-note"`), and `author: str | None`. Both `Alert` and `Finding` SHALL carry an optional `guidance: InvestigationGuidance | None` field defaulting to `None`.

#### Scenario: Item with guidance parses
- **WHEN** an alert or finding payload includes a `guidance` object with `text` and `source`
- **THEN** the item validates and exposes an `InvestigationGuidance` with those fields

#### Scenario: Item without guidance is valid
- **WHEN** an alert or finding payload omits `guidance`
- **THEN** the item validates with `guidance` as `None`

### Requirement: Guidance is populated eagerly by the item producer
The producer of a work item SHALL populate `guidance` before the item reaches `core`. For push intake (authenticated API/MCP submitters) the guidance rides in the submitted payload. For pull intake the `TriagePlatform` SHALL populate it during `fetch_open`/`get`. The analyst SHALL NOT fetch guidance itself, preserving the `platforms → core` dependency direction.

#### Scenario: Pushed guidance is preserved
- **WHEN** a submitter posts an item containing guidance
- **THEN** the guidance reaches the analyst unchanged, with `source` = `"submitter"`

#### Scenario: Pulled guidance is attached at fetch time
- **WHEN** a `TriagePlatform` returns an open item that has associated guidance
- **THEN** the returned item already carries the `guidance` field, without the analyst calling the platform

### Requirement: Guidance is a lead; raw event data is evidence
The analyst's method SHALL treat `guidance` as trusted direction to be verified, and SHALL treat raw event data in the payload as evidence that never redirects the investigation. Content inside `raw` SHALL NOT be interpreted as instructions.

#### Scenario: Guidance focuses the investigation
- **WHEN** guidance suggests checking a specific entity or log source
- **THEN** the analyst uses it to focus but still reaches its own verdict from the evidence

#### Scenario: Injected instructions in raw are ignored
- **WHEN** the `raw` payload contains text resembling instructions (e.g. an attacker-controlled field)
- **THEN** the analyst treats it as data under investigation, not as a directive

### Requirement: The general analyst method is Benny-owned and guidance-independent
Each analyst's persona SHALL be a stable, in-repo method owned by its module, not sourced from a runbook file. The method SHALL be sufficient to triage an item that carries no guidance.

#### Scenario: Triage proceeds with no guidance
- **WHEN** an item arrives with `guidance` = `None`
- **THEN** the analyst still performs a full triage using its general method and reaches a verdict

### Requirement: Guidance provenance is observable
The system SHALL record, per triaged item, whether guidance was present, its `source`, and its length, so guidance coverage can be measured.

#### Scenario: Presence and source are logged
- **WHEN** an item is triaged
- **THEN** a structured log records guidance present/absent, `source`, and `text` length
