## MODIFIED Requirements

### Requirement: Finding is the VM input contract
The system SHALL define a `Finding` input with at least: `id`, `type` (vuln class, metadata and dedup input), `cve`, `asset`, `cvss: float`, `title`, `description`, `source`, `detected_at`, `raw`, and an optional `guidance: InvestigationGuidance | None`. It mirrors the `Alert` shape so it fits the `AnalystModule` pattern.

#### Scenario: Valid finding parses
- **WHEN** a payload with all required `Finding` fields is validated
- **THEN** a `Finding` is produced with `cvss` as a float and `type` available as metadata

### Requirement: VulnModule implements the AnalystModule contract
The system SHALL provide a `VulnModule` with `name = "vuln_mgmt"`, `input_type = Finding`, `accepts(raw)` for finding-shaped payloads, `dedup_key(finding)`, and `investigate(finding, caps)` returning an `Investigation`. The analyst uses the module's general triage method; per-finding direction, if any, arrives via `finding.guidance`. There is no runbook selection.

#### Scenario: accepts recognizes findings only
- **WHEN** `accepts` is called with a valid finding payload
- **THEN** it returns `True`, and returns `False` for a non-finding payload (e.g. a SIEM alert missing `cve`/`cvss`)

#### Scenario: dedup key reflects material change
- **WHEN** `dedup_key(finding)` is called
- **THEN** it returns `"{cve}:{asset}:{cvss}"`, so the same finding at the same CVSS dedups but a rescored CVSS produces a new key

#### Scenario: investigate produces a VM triage report
- **WHEN** `VulnModule.investigate(finding, caps)` runs
- **THEN** it returns an `Investigation` whose report payload is a `VulnTriageReport` (exploitable, priority, SLA, evidence) and whose `outcome` carries a disposition and priority
