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

### Requirement: The analyst method and guidance are internal to the module
The system SHALL keep the analyst's steering internal to the module and off the `AnalystModule` contract: the general investigation method is the module's own in-repo persona, and per-item direction arrives via the item's `guidance` field. Neither is exposed through `name`/`input_type`/`accepts`/`investigate`.

#### Scenario: Steering is not on the contract
- **WHEN** the `AnalystModule` contract is inspected
- **THEN** it exposes only `name`, `input_type`, `accepts`, and `investigate` — no runbook or guidance selection surface

#### Scenario: Method drives the persona
- **WHEN** a module investigates an item
- **THEN** the analyst persona is the module's general method, and any item `guidance` is applied as a lead within that method

