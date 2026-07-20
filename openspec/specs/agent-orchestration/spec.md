# agent-orchestration Specification

## Purpose
TBD - created by archiving change module-contract-and-orchestrator. Update Purpose after archive.
## Requirements
### Requirement: OrchestratorAgent exposes a single handle seam
The system SHALL provide `OrchestratorAgent.handle(raw: dict, hint: str | None = None) -> Investigation | None`. It SHALL resolve an `AnalystModule`, delegate the investigation to it with the shared `Capabilities`, persist the resulting `Investigation`, and return it. It SHALL return `None` when no module can handle the request.

#### Scenario: Explicit hint dispatches to the named module
- **WHEN** `handle(raw, hint="siem")` is called
- **THEN** the SIEM module is resolved and its `investigate` is invoked, and the returned `Investigation` is persisted

#### Scenario: No module can handle the request
- **WHEN** `handle(raw)` is called and no registered module's `accepts()` returns `True`
- **THEN** it returns `None` and nothing is persisted

---

### Requirement: Routing runs at two speeds
The system SHALL dispatch deterministically when a `hint` is supplied, invoking no LLM classifier. When no `hint` is supplied it SHALL resolve via module `accepts()`, and SHALL only invoke an LLM classifier when more than one registered module could apply.

#### Scenario: Deterministic path when hint is present
- **WHEN** `handle(raw, hint="siem")` is called
- **THEN** module resolution makes no LLM classification call

#### Scenario: Free-form path with a single applicable module
- **WHEN** `handle(raw)` is called with no hint and exactly one registered module accepts the payload
- **THEN** that module is selected without an LLM classification call

---

### Requirement: Router returns one module result, extensible to synthesis
The system SHALL route each request to exactly one module. The `handle()` return type SHALL be defined so that a future synthesized multi-module result can be returned without changing the `handle()` signature or its callers.

#### Scenario: Exactly one module handles a request
- **WHEN** `handle()` routes a request
- **THEN** exactly one module's `investigate` is invoked

---

### Requirement: The SIEM investigation flow is preserved through the orchestrator
The system SHALL preserve the existing SIEM `/investigate` behavior when the flow is routed through `OrchestratorAgent` + `SIEMModule`. The produced `Investigation`/`IncidentReport` structure is unchanged except that the former `runbook` field is replaced by `guidance_source`, which records the provenance of the applied guidance (or `None`).

#### Scenario: Existing investigate route behavior is preserved
- **WHEN** an alert is submitted to `POST /investigate`
- **THEN** the response is an `Investigation` whose report carries the same fields as before except that `guidance_source` records the guidance provenance (or `None`) in place of the removed `runbook` field

---

### Requirement: MCP exposes investigable domains, not runbooks
The MCP server SHALL expose a `list_modules` tool that returns the registered modules and the alert/finding types they investigate, replacing `list_runbooks`. The tool answers "what can Benny investigate" from the `ModuleRegistry`.

#### Scenario: Module discovery replaces runbook listing
- **WHEN** an MCP client calls `list_modules`
- **THEN** it receives the registered module names and their input types, and no `list_runbooks` tool is exposed

