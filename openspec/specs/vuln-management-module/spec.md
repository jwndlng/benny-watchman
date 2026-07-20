# vuln-management-module Specification

## Purpose
TBD - created by archiving change vuln-management-module. Update Purpose after archive.
## Requirements
### Requirement: Finding is the VM input contract
The system SHALL define a `Finding` input with at least: `id`, `type` (vuln class, metadata and dedup input), `cve`, `asset`, `cvss: float`, `title`, `description`, `source`, `detected_at`, `raw`, and an optional `guidance: InvestigationGuidance | None`. It mirrors the `Alert` shape so it fits the `AnalystModule` pattern.

#### Scenario: Valid finding parses
- **WHEN** a payload with all required `Finding` fields is validated
- **THEN** a `Finding` is produced with `cvss` as a float and `type` available as metadata

---

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

---

### Requirement: VM triage report shape
The system SHALL define a `VulnTriageReport` with at least: `finding_id`, `exploitable: bool`, `priority: str`, `remediation_sla_days: int | None`, `confidence: float`, `summary`, `affected_assets`, `evidence`, `recommended_actions`, and `investigation_steps`.

#### Scenario: Report captures a triage decision
- **WHEN** a VM investigation completes
- **THEN** its report indicates whether the vulnerability is exploitable in context, a priority, and a recommended remediation timeline

---

### Requirement: VM reuses the DataAgent pattern and owns its intel tool
The VM analyst SHALL consult an asset/vuln inventory via a `DataAgent` selected from `Capabilities.data` (dev: a seeded SQLite source named `asset_inventory`). Threat-intel enrichment (CVE/EPSS/KEV) SHALL be a VM-owned composite tool (deterministic; a stub in dev), exposed to the analyst — not a shared horizontal capability.

#### Scenario: VM analyst has data and intel tools
- **WHEN** the VM module builds its analyst
- **THEN** the analyst can query the `asset_inventory` data source and call the vuln-intel tool

---

### Requirement: VM is routable and idempotent
`VulnModule` SHALL be registered in the `ModuleRegistry`. `POST /findings` SHALL submit a finding via `OrchestratorAgent.handle(raw, hint="vuln_mgmt")`, returning `202` for a fresh triage and `200` for a deduped repeat, consistent with the SIEM `/investigate` contract.

#### Scenario: Finding routed to the VM module
- **WHEN** a finding is submitted to `POST /findings`
- **THEN** the VM module produces the investigation and it is persisted

#### Scenario: Duplicate finding is deduped
- **WHEN** the same finding (same cve/asset/cvss) is submitted twice
- **THEN** the first returns `202` and the second returns `200` with the same investigation id, and only one investigation is stored

