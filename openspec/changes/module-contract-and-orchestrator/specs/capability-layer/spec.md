## ADDED Requirements

### Requirement: Capabilities is a typed container of shared instances
The system SHALL provide a `Capabilities` container holding configured horizontal capability instances — at minimum `data: dict[str, BaseDataAgent]` keyed by source name, plus an optional identity capability. It SHALL be constructed once at the composition root and passed to a module's `investigate()`. It SHALL hold instances only, not domain logic.

#### Scenario: Data agents are accessible by source name
- **WHEN** a module reads `caps.data["security_logs"]`
- **THEN** it receives the initialized `BaseDataAgent` registered for that source name

#### Scenario: Identity is optional
- **WHEN** no identity backend is configured at startup
- **THEN** the identity capability on `caps` is `None` and a module consuming it degrades gracefully rather than failing

---

### Requirement: Modules select capabilities; the composition root wires them
A module SHALL select the capability instances it consults from `caps`, and capability instances SHALL be constructed centrally from configuration rather than inside module code. The same instances SHALL be shared across the REST and MCP entry points.

#### Scenario: SIEM selects the capabilities it needs
- **WHEN** the SIEM module builds its analyst during `investigate`
- **THEN** it passes the `caps.data` values as the analyst's `data_agents` and the `caps` identity as its `okta_client`

#### Scenario: Capabilities are built once and shared
- **WHEN** the application starts
- **THEN** capability instances are constructed a single time at the composition root and the same `Capabilities` is used by both the REST orchestrator and the MCP tools
