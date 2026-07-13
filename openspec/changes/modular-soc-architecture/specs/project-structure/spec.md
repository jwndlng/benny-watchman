## ADDED Requirements

### Requirement: Source is organized along a horizontal/vertical seam
The system SHALL organize `src/` into three top-level areas that make the reuse boundary visible: `core/` for the domain-agnostic framework and orchestration, `capabilities/` for cross-cutting horizontal agents and tools shared by all domains, and `modules/` for per-domain verticals. This is a behavior-preserving relocation of existing code — no new abstractions are introduced in this slice.

#### Scenario: Core framework is importable from its new location
- **WHEN** the application imports the base agent and orchestration components
- **THEN** `BaseAgent` resolves under `src/core/agents/` and `Orchestrator` and the runbook/module registry resolve under `src/core/orchestration/`

#### Scenario: Capabilities are grouped under a horizontal package
- **WHEN** the application imports data, identity, or enrichment components
- **THEN** the DataAgent classes resolve under `src/capabilities/data/`, the Okta identity code and `UserProfile` under `src/capabilities/identity/`, and the enrichment agent under `src/capabilities/enrichment/`

#### Scenario: SIEM-specific code is isolated in its module
- **WHEN** the application imports SIEM investigation code
- **THEN** the SIEM analyst, the detection-engineer agent, the `Alert` and `IncidentReport` schemas, and the SIEM runbooks all resolve under `src/modules/siem/`

---

### Requirement: MCP transport code lives under a dedicated package
The system SHALL place MCP code under a dedicated `src/mcp/` package split by role: `src/mcp/server/` for code that exposes Benny AS an MCP server, and `src/mcp/clients/` for code that lets Benny act as a client of external MCP servers. No MCP module SHALL remain at the `src/` package root, and the MCP-server assembly SHALL NOT remain inline in `src/api/app.py`.

#### Scenario: Server code is grouped under mcp/server
- **WHEN** the application assembles and mounts the MCP server
- **THEN** the bearer-auth middleware, the tool registration, and the FastMCP app assembly resolve under `src/mcp/server/`

#### Scenario: No MCP module remains at the package root
- **WHEN** the `src/` package root is inspected after the refactor
- **THEN** `src/mcp_auth.py` and `src/mcp_tools.py` no longer exist and their contents live under `src/mcp/server/`

#### Scenario: A client package exists for external MCP consumers
- **WHEN** the codebase is inspected for MCP-client integration
- **THEN** an `src/mcp/clients/` package exists as the home for external MCP consumers (e.g. ClickHouse via stdio), even if empty at the end of this slice

#### Scenario: API mounts the assembled server rather than assembling it
- **WHEN** `src/api/app.py` wires the MCP endpoint
- **THEN** it imports an already-assembled server from `src/mcp/server/` and mounts it, and does not itself register tools or construct the FastMCP app inline

---

### Requirement: Shared infrastructure remains outside the seam
The system SHALL keep infrastructure that is neither vertical nor a capability at a shared location: the query engines, application config, persistence models, and utilities. The persistence `Investigation` record SHALL NOT be reshaped or relocated into `core/` in this slice, because its idempotency-envelope redesign is a behavioral change deferred to a later change.

#### Scenario: Engines remain shared infrastructure
- **WHEN** the data capability and the persistence layer both need a query backend
- **THEN** `QueryEngine` and its implementations resolve under `src/engines/` and are importable by both `src/capabilities/data/` and `src/models.py`

#### Scenario: Investigation persistence is unchanged in this slice
- **WHEN** the refactor completes
- **THEN** the `Investigation` schema and `InvestigationModel` retain their current shape and behavior, and no dedup key, `outcome`, or generic report payload is introduced

---

### Requirement: Dependency direction flows verticals → horizontals → framework
The restructure SHALL enforce that `src/capabilities/` and the framework code in `src/core/agents/` do not import from `src/modules/`. Module (vertical) code MAY import from `capabilities/` and `core/`; the reverse SHALL NOT hold. The legacy deterministic `Orchestrator` retains a direct dependency on the SIEM analyst until the `AnalystModule` contract inverts it; this single transitional edge SHALL be confined to `src/core/orchestration/` and removed by the module-contract change.

#### Scenario: Capabilities do not depend on modules
- **WHEN** the import graph of `src/capabilities/` is inspected
- **THEN** no module under `src/capabilities/` imports from `src/modules/`

#### Scenario: Framework agents do not depend on modules
- **WHEN** the import graph of `src/core/agents/` is inspected
- **THEN** it does not import from `src/modules/`

#### Scenario: The transitional core→module edge is isolated
- **WHEN** the legacy `Orchestrator` references the SIEM analyst before the module contract exists
- **THEN** that dependency is confined to `src/core/orchestration/` and is the only import from `core/` into `modules/`

---

### Requirement: The refactor preserves runtime behavior
The relocation SHALL NOT change runtime behavior, public API contracts, or the MCP tool surface. The existing automated test suite SHALL pass without modification other than import-path updates.

#### Scenario: Existing tests pass after the move
- **WHEN** the full test suite is run after the refactor
- **THEN** every test that passed before the refactor passes after it, with changes limited to import paths

#### Scenario: REST endpoints behave identically
- **WHEN** a client calls `POST /investigate` and the other existing routes after the refactor
- **THEN** the request/response behavior is identical to before the refactor

#### Scenario: MCP tool surface is unchanged
- **WHEN** an MCP client connects to `/mcp` with a valid bearer token after the refactor
- **THEN** the same tools (`list_runbooks`, `lookup_data`) are available with the same schemas and behavior as before
