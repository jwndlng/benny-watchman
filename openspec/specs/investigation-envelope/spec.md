# investigation-envelope Specification

## Purpose
TBD - created by archiving change vuln-management-module. Update Purpose after archive.
## Requirements
### Requirement: Investigation report is a domain-agnostic payload
`Investigation.report` SHALL be a serialized, domain-agnostic payload (`dict[str, object] | None`) rather than a module-specific type. Each module SHALL keep its own typed report internally and serialize it into the envelope. As a result, `src/schemas/investigation.py` SHALL NOT import any module (`src/modules/...`) type.

#### Scenario: Envelope has no module imports
- **WHEN** the import graph of `src/schemas/investigation.py` and `src/models.py` is inspected
- **THEN** neither imports from `src/modules/`

#### Scenario: SIEM report round-trips through the envelope
- **WHEN** a SIEM investigation is persisted and re-read
- **THEN** its report payload contains the same `IncidentReport` fields as before the generalization (the `/reports` response is unchanged)

---

### Requirement: Investigation carries a generic outcome
The system SHALL provide a core `Outcome` type (`disposition: str`, `priority: str`) and an optional `Investigation.outcome` field, so investigations from any module can be listed and compared cross-domain without deserializing their reports.

#### Scenario: Modules populate a comparable outcome
- **WHEN** a SIEM or VM investigation completes
- **THEN** its `outcome` carries a `disposition` and `priority` mapped from the module's verdict/severity, using the same `Outcome` type

---

### Requirement: SIEM behavior is preserved under the generalization
Generalizing the envelope SHALL NOT change SIEM behavior or the existing API responses. The existing test suite SHALL pass unchanged apart from how the SIEM report is written into the envelope.

#### Scenario: SIEM suite stays green
- **WHEN** the full test suite is run after the generalization
- **THEN** all previously passing SIEM and route tests still pass

