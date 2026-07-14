## MODIFIED Requirements

### Requirement: Orchestrator receives pre-initialized DataAgents
The system SHALL provide capabilities — including pre-initialized `BaseDataAgent`s — to modules via a `Capabilities` container rather than passing `data_agents` directly to a monolithic `Orchestrator`. The `OrchestratorAgent` SHALL resolve an `AnalystModule` from the `ModuleRegistry` and delegate investigation to it, forwarding `Capabilities` at investigation time. Initialization of data agents remains the caller's responsibility — neither the orchestrator nor the module SHALL call `initialize()` again.

#### Scenario: Investigation uses capability-provided DataAgents
- **WHEN** `OrchestratorAgent.handle(raw, hint="siem")` is called with a `Capabilities` containing one initialized DataAgent
- **THEN** the SIEM module produces the investigation via an `AnalystAgent` that has that DataAgent's `query_{name}` tool

#### Scenario: DataAgents are not re-initialized
- **WHEN** the orchestrator delegates to a module
- **THEN** it forwards the pre-initialized DataAgents through `Capabilities` without calling `initialize()`
