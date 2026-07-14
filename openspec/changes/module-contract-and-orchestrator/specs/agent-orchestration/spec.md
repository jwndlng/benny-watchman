## ADDED Requirements

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
The system SHALL preserve the existing SIEM `/investigate` behavior when the flow is routed through `OrchestratorAgent` + `SIEMModule`. The deterministic `Orchestrator` is replaced without changing the produced `Investigation`/`IncidentReport` structure.

#### Scenario: Existing investigate route behavior is unchanged
- **WHEN** an alert is submitted to `POST /investigate` after the refactor
- **THEN** the response is an `Investigation` whose `runbook` matches the alert type (or `generic`) and whose report carries the same fields as before, and the existing route tests pass
