## MODIFIED Requirements

### Requirement: The SIEM investigation flow is preserved through the orchestrator
The system SHALL preserve the existing SIEM `/investigate` behavior when the flow is routed through `OrchestratorAgent` + `SIEMModule`. The produced `Investigation`/`IncidentReport` structure is unchanged except that the former `runbook` field is replaced by `guidance_source`, which records the provenance of the applied guidance (or `None`).

#### Scenario: Existing investigate route behavior is preserved
- **WHEN** an alert is submitted to `POST /investigate`
- **THEN** the response is an `Investigation` whose report carries the same fields as before except that `guidance_source` records the guidance provenance (or `None`) in place of the removed `runbook` field

## ADDED Requirements

### Requirement: MCP exposes investigable domains, not runbooks
The MCP server SHALL expose a `list_modules` tool that returns the registered modules and the alert/finding types they investigate, replacing `list_runbooks`. The tool answers "what can Benny investigate" from the `ModuleRegistry`.

#### Scenario: Module discovery replaces runbook listing
- **WHEN** an MCP client calls `list_modules`
- **THEN** it receives the registered module names and their input types, and no `list_runbooks` tool is exposed
