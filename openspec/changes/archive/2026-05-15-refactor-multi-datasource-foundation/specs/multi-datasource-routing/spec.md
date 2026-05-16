## ADDED Requirements

### Requirement: QueryEngine defines the query-only contract
The system SHALL provide a `QueryEngine` ABC containing exactly four methods — `list_tables`, `get_schema`, `get_sample`, `run_query` — with no persistence methods. Any class implementing `QueryEngine` SHALL be usable as a DataAgent backend without implementing storage concerns.

#### Scenario: QueryEngine excludes persistence methods
- **WHEN** a class implements `QueryEngine`
- **THEN** it is not required to implement `init_store`, `upsert`, `fetch`, or `fetch_all`

#### Scenario: SQLiteEngine satisfies QueryEngine
- **WHEN** `SQLiteEngine` is checked against `QueryEngine`
- **THEN** it passes isinstance/ABC checks and all four query methods are callable

---

### Requirement: BaseDataAgent has a name, description, and lazy initialization
The system SHALL provide `BaseDataAgent` as an abstract base class with a `name: str` property identifying the data source and a `routing_description: str` property holding a concise summary of available data. The description SHALL be built during `initialize()`, not at construction time, because it requires I/O against the backend.

#### Scenario: routing_description unavailable before initialization
- **WHEN** `run()` is called on a `BaseDataAgent` before `initialize()` has completed
- **THEN** the system SHALL raise `RuntimeError` with a message indicating initialization is required

#### Scenario: routing_description built from schema and samples
- **WHEN** `initialize()` is called on a DataAgent backed by a non-empty backend
- **THEN** `routing_description` is populated with a formatted summary of available tables, their fields, and at least one sample event per table

---

### Requirement: DataAgent initialization fails fast on unreachable backend
The system SHALL treat a backend that is unreachable during `initialize()` as a hard failure. The exception SHALL propagate to the caller rather than being swallowed, so that server startup fails before accepting any requests.

#### Scenario: Backend unreachable at startup
- **WHEN** `initialize()` is called and the backend raises a connection error
- **THEN** the exception propagates unhandled and server startup is aborted

---

### Requirement: SQLiteDataAgent preserves current DataAgent behavior
The system SHALL provide `SQLiteDataAgent` as a concrete `BaseDataAgent` that exposes `list_tables`, `get_schema`, `get_sample`, and `run_query` tools backed by `SQLiteEngine`. Behavior SHALL be identical to the current `DataAgent` implementation for all existing test cases.

#### Scenario: Existing integration tests pass unchanged
- **WHEN** the full test suite is run after the refactor
- **THEN** all tests that passed before the refactor continue to pass

#### Scenario: SQLiteDataAgent query returns rows
- **WHEN** `SQLiteDataAgent.run("find all events for user X")` is called on a populated DB
- **THEN** it returns a `DataModel` with non-empty rows and a non-empty notes field

---

### Requirement: AnalystAgent registers one tool per DataAgent
The system SHALL accept a `data_agents: list[BaseDataAgent]` parameter in `AnalystAgent.__init__` and register exactly one tool per DataAgent. The tool name SHALL be `query_{agent.name}` and the tool docstring SHALL be `agent.routing_description`.

#### Scenario: Single DataAgent registered as query tool
- **WHEN** `AnalystAgent` is constructed with one `BaseDataAgent` named `"security_logs"`
- **THEN** the underlying PydanticAI agent has a tool named `query_security_logs`

#### Scenario: Multiple DataAgents registered as separate tools
- **WHEN** `AnalystAgent` is constructed with two DataAgents named `"auth_siem"` and `"network_siem"`
- **THEN** the underlying PydanticAI agent has exactly two query tools: `query_auth_siem` and `query_network_siem`

---

### Requirement: AnalystAgent rejects duplicate DataAgent names
The system SHALL raise `ValueError` at construction time if two or more DataAgents in the provided list share the same `name`, preventing ambiguous tool registration.

#### Scenario: Duplicate names rejected at construction
- **WHEN** `AnalystAgent` is constructed with two DataAgents that have identical `name` values
- **THEN** `ValueError` is raised before any tools are registered

---

### Requirement: Orchestrator receives pre-initialized DataAgents
The system SHALL pass `data_agents: list[BaseDataAgent]` to `Orchestrator` at construction. The Orchestrator SHALL forward them to `AnalystAgent` at investigation time without calling `initialize()` again — initialization is the caller's responsibility.

#### Scenario: Investigation uses provided DataAgents
- **WHEN** `Orchestrator.investigate(alert)` is called with one DataAgent available
- **THEN** the resulting investigation was produced by an `AnalystAgent` that had access to that DataAgent's query tool
