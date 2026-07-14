# analyst-module-contract Specification

## Purpose
TBD - created by archiving change module-contract-and-orchestrator. Update Purpose after archive.
## Requirements
### Requirement: AnalystModule defines the per-domain contract
The system SHALL provide an `AnalystModule` Protocol with `name: str`, `input_type: type`, `accepts(raw: dict) -> bool`, and `investigate(inp, caps: Capabilities) -> Investigation`. Each triage domain SHALL be expressed as a class implementing this Protocol, so that adding a domain requires adding a module rather than modifying core code.

#### Scenario: SIEM module implements the contract
- **WHEN** `SIEMModule` is checked against the `AnalystModule` Protocol
- **THEN** its `name` is `"siem"`, its `input_type` is `Alert`, and `accepts` and `investigate` are callable

#### Scenario: accepts identifies a handleable payload
- **WHEN** `accepts(raw)` is called on the SIEM module with an alert-shaped dict
- **THEN** it returns `True`, and returns `False` for a payload that is not a valid alert

---

### Requirement: ModuleRegistry registers and resolves modules
The system SHALL provide a `ModuleRegistry` that registers modules by `name`, returns a module by explicit name, and resolves a module for a raw payload via each module's `accepts()`. Registering two modules with the same `name` SHALL raise `ValueError`.

#### Scenario: Resolve by explicit name
- **WHEN** `registry.get("siem")` is called after the SIEM module is registered
- **THEN** it returns the SIEM module, and returns `None` for an unregistered name

#### Scenario: Resolve by accepts
- **WHEN** `registry.resolve(raw)` is called with an alert-shaped dict and SIEM is the only module whose `accepts()` returns `True`
- **THEN** it returns the SIEM module

#### Scenario: Duplicate module names rejected
- **WHEN** two modules sharing the same `name` are registered
- **THEN** `ValueError` is raised

---

### Requirement: Runbook selection remains internal to the module
The system SHALL keep playbook (runbook) selection inside the module. The SIEM module SHALL match a runbook by alert type using its own registry and SHALL NOT expose runbook selection through the `AnalystModule` contract. `RunbookRegistry` is a within-module concern, distinct from `ModuleRegistry`.

#### Scenario: SIEM matches a runbook internally
- **WHEN** the SIEM module investigates an alert whose type matches a loaded runbook
- **THEN** it selects that runbook as the analyst persona, falling back to the `generic` runbook for an unmatched type, without the orchestrator being involved in runbook selection

