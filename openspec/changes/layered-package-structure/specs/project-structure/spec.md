## MODIFIED Requirements

### Requirement: Source is organized along a horizontal/vertical seam
The system SHALL organize `src/` so that **two** axes are visible: *where code is shared* (horizontal vs vertical) and *what kind of unit it is* (LLM sub-agent vs deterministic tool). It SHALL use `core/` for the domain-agnostic framework and orchestration; `capabilities/` for cross-cutting **horizontal** competences shared by all domains, split by boundary kind into `capabilities/subagents/` (LLM loops) and `capabilities/tools/` (deterministic composites); and `modules/` for per-domain **verticals**, each a self-contained package that owns its domain models under `<module>/schemas/` and any module-local tools under `<module>/tools/`. This remains a behavior-preserving relocation — no new abstractions are introduced.

#### Scenario: Core framework is importable from its new location
- **WHEN** the application imports the base agent and orchestration components
- **THEN** `BaseAgent` resolves under `src/core/agents/` and the orchestrator and the runbook/module registries resolve under `src/core/orchestration/`

#### Scenario: Horizontal capabilities are grouped by boundary kind
- **WHEN** the application imports the shared data or identity components
- **THEN** the DataAgent classes resolve under `src/capabilities/subagents/data/`, and the Okta identity code, `IdentityCapability`, and `UserProfile` resolve under `src/capabilities/tools/identity/`

#### Scenario: Only genuinely horizontal code lives in capabilities
- **WHEN** the `src/capabilities/` package is inspected
- **THEN** it contains only competences consumed by more than one domain (data, identity), and a tool used by a single module does NOT live there

#### Scenario: A module is a self-contained package
- **WHEN** the application imports a module's investigation code
- **THEN** the module's analyst and `AnalystModule` implementation resolve directly under `src/modules/<module>/`, its domain models resolve under `src/modules/<module>/schemas/`, its module-local tools resolve under `src/modules/<module>/tools/`, and its runbooks under `src/modules/<module>/runbooks/` (e.g. SIEM's `Alert`/`IncidentReport` under `src/modules/siem/schemas/`; VM's `Finding`/`VulnTriageReport` under `src/modules/vuln_mgmt/schemas/` and its vuln-intel tool under `src/modules/vuln_mgmt/tools/`)

---

### Requirement: MCP transport code lives under a dedicated package
The system SHALL place MCP code under `src/adapters/mcp/`, split by role: `adapters/mcp/server/` for code that exposes Benny AS an MCP server, and `adapters/mcp/clients/` for code that lets Benny act as a client of external MCP servers. The MCP-server assembly SHALL NOT be inlined into the API app; the API SHALL mount an already-assembled server.

#### Scenario: Server code is grouped under adapters/mcp/server
- **WHEN** the application assembles and mounts the MCP server
- **THEN** the bearer-auth middleware, the tool registration, and the FastMCP app assembly resolve under `src/adapters/mcp/server/`

#### Scenario: A client package exists for external MCP consumers
- **WHEN** the codebase is inspected for MCP-client integration
- **THEN** an `src/adapters/mcp/clients/` package exists as the home for external MCP consumers (e.g. ClickHouse via stdio), even if empty

#### Scenario: API mounts the assembled server rather than assembling it
- **WHEN** `src/adapters/api/app.py` wires the MCP endpoint
- **THEN** it imports an already-assembled server from `src/adapters/mcp/server/` and mounts it, and does not itself register tools or construct the FastMCP app inline

---

### Requirement: Dependency direction flows verticals → horizontals → framework
The layout SHALL enforce an inward dependency direction. `core/` SHALL NOT import from `modules/` at all, and SHALL NOT import from `adapters/` at runtime; its only permitted `adapters/` reference is a `TYPE_CHECKING`-only import of the persistence model (`InvestigationModel`) used as a dependency-injection type hint, confined to `core/orchestration/` pending extraction of a persistence port into `core/`. `capabilities/` MAY import `core/` and `adapters/engines` but SHALL NOT import `modules/`. `modules/` MAY import `core/` and `capabilities/` but SHALL NOT import another module. `adapters/` (the outer ring, including the composition root `adapters/api/app.py`) MAY import `core/`, `capabilities/`, and `modules/` to wire the application.

#### Scenario: Capabilities do not depend on modules
- **WHEN** the import graph of `src/capabilities/` is inspected
- **THEN** no module under `src/capabilities/` imports from `src/modules/`

#### Scenario: Core does not depend on modules
- **WHEN** the import graph of `src/core/` is inspected
- **THEN** it imports nothing from `src/modules/`

#### Scenario: The transitional core→adapters typing edge is isolated
- **WHEN** `src/core/` references an adapter
- **THEN** the only such reference is the `TYPE_CHECKING` import of `InvestigationModel` from `src/adapters/persistence` for the orchestrator's injected `persistence` type hint, it is confined to `src/core/orchestration/`, and it introduces no runtime import from `core/` into `adapters/`

#### Scenario: Modules do not depend on each other
- **WHEN** the import graph of any `src/modules/<module>/` is inspected
- **THEN** it does not import from another sibling module

---

### Requirement: The refactor preserves runtime behavior
The relocation SHALL NOT change runtime behavior, public API contracts, or the MCP tool surface. The existing automated test suite SHALL pass with changes limited to import-path updates and the removal of unwired code.

#### Scenario: Existing tests pass after the move
- **WHEN** the full test suite is run after the refactor
- **THEN** every test that passed before the refactor passes after it, with changes limited to import paths

#### Scenario: REST endpoints behave identically
- **WHEN** a client calls the existing routes (`POST /investigate`, `POST /findings`, `POST /triage/run`, …) after the refactor
- **THEN** the request/response behavior is identical to before the refactor

#### Scenario: MCP tool surface is unchanged
- **WHEN** an MCP client connects to `/mcp` with a valid bearer token after the refactor
- **THEN** the same tools that were available before the refactor are available with identical schemas and behavior

## ADDED Requirements

### Requirement: The outer I/O ring is grouped under an adapters package
The system SHALL group all code that touches the outside world under `src/adapters/`: inbound transports (`adapters/api/`, `adapters/mcp/`) and outbound adapters (`adapters/platforms/` for triage platforms, `adapters/engines/` for query engines, and `adapters/persistence.py` for investigation storage). No such I/O code SHALL remain a flat peer of `core/` at the `src/` root. These adapters depend inward on `core/`, `capabilities/`, and `modules/`.

#### Scenario: Inbound transports live under adapters
- **WHEN** the application serves the REST API and the MCP endpoint
- **THEN** the FastAPI app and routes resolve under `src/adapters/api/` and the MCP packages under `src/adapters/mcp/`

#### Scenario: Outbound adapters live under adapters
- **WHEN** the application reads/writes external systems
- **THEN** the `QueryEngine` and its implementations resolve under `src/adapters/engines/`, the `TriagePlatform` and its implementations under `src/adapters/platforms/`, and investigation persistence under `src/adapters/persistence.py`

#### Scenario: No I/O code remains at the package root
- **WHEN** the `src/` package root is inspected after the refactor
- **THEN** `src/api/`, `src/mcp/`, `src/platforms/`, `src/engines/`, and `src/models.py` no longer exist and their contents live under `src/adapters/`

## REMOVED Requirements

### Requirement: Shared infrastructure remains outside the seam
**Reason**: Superseded by "The outer I/O ring is grouped under an adapters package." The query engines and persistence are no longer scattered at the `src/` root as un-layered "shared infrastructure" — they are outbound adapters and now live under `src/adapters/`. The clause deferring the `Investigation` idempotency-envelope redesign is also obsolete: that redesign shipped in the `investigation-idempotency` change.

**Migration**: Import `QueryEngine` from `src.adapters.engines` (was `src.engines`) and investigation persistence from `src.adapters.persistence` (was `src.models`). No behavior change.
