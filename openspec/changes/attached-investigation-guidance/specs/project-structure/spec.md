## MODIFIED Requirements

### Requirement: Source is organized along a horizontal/vertical seam
The system SHALL organize `src/` into three top-level areas that make the reuse boundary visible: `core/` for the domain-agnostic framework and orchestration, `capabilities/` for cross-cutting horizontal agents and tools shared by all domains, and `modules/` for per-domain verticals.

#### Scenario: Core framework is importable from its new location
- **WHEN** the application imports the base agent and orchestration components
- **THEN** `BaseAgent` resolves under `src/core/agents/` and the orchestrator and module registry resolve under `src/core/orchestration/`

#### Scenario: Capabilities are grouped under a horizontal package
- **WHEN** the application imports data, identity, or enrichment components
- **THEN** the DataAgent classes resolve under `src/capabilities/data/`, the Okta identity code and `UserProfile` under `src/capabilities/identity/`, and the enrichment agent under `src/capabilities/enrichment/`

#### Scenario: SIEM-specific code is isolated in its module
- **WHEN** the application imports SIEM investigation code
- **THEN** the SIEM analyst, the detection-engineer agent, and the `Alert` and `IncidentReport` schemas resolve under `src/modules/siem/`

### Requirement: The refactor preserves runtime behavior
The relocation SHALL NOT change runtime behavior or public API contracts except where a later change specifies otherwise. The existing automated test suite SHALL pass without modification other than import-path updates.

#### Scenario: Existing tests pass after the move
- **WHEN** the full test suite is run after the refactor
- **THEN** every test that passed before the refactor passes after it, with changes limited to import paths

#### Scenario: REST endpoints behave identically
- **WHEN** a client calls `POST /investigate` and the other existing routes
- **THEN** the request/response behavior matches the current contract

#### Scenario: MCP tool surface
- **WHEN** an MCP client connects to `/mcp` with a valid bearer token
- **THEN** the available tools are `list_modules` and `lookup_data`
