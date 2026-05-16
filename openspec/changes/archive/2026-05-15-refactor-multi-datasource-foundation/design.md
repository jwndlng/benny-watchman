## Context

`DataAgent` currently treats all backends as one unified query space: multiple `Engine` instances are merged into a single system prompt, and `run_query` always delegates to the first engine. The `Engine` ABC conflates two unrelated concerns — query execution and persistence — making it impossible to implement a query-only backend (Elasticsearch, ClickHouse) without also stubbing out persistence methods.

`AnalystAgent` constructs its own `DataAgent` internally via `DataAgent.create()`, which hardwires the SQLite backend and makes it impossible to pass alternative data sources without changing AnalystAgent's constructor.

## Goals / Non-Goals

**Goals:**
- Separate `QueryEngine` (query-only ABC) from persistence, which stays on `SQLiteEngine` directly
- Introduce `BaseDataAgent` with `name`, `description`, and `initialize()` — so each agent is self-describing and startup-validated
- `SQLiteDataAgent` replaces the current `DataAgent` with identical behavior
- `AnalystAgent` accepts `data_agents: list[BaseDataAgent]` and registers one tool per agent dynamically
- Zero behavior change — all existing tests pass unchanged

**Non-Goals:**
- Implementing any new backend (Elasticsearch, ClickHouse)
- Changing the investigation flow, API, or persistence schema
- Per-agent call budget tracking (deferred — overall cap via `UsageLimits` is sufficient for now)

## Decisions

### 1. `QueryEngine` ABC contains only the four query methods

`Engine` currently defines eight methods: four query (`list_tables`, `get_schema`, `get_sample`, `run_query`) and four persistence (`init_store`, `upsert`, `fetch`, `fetch_all`). These have no shared semantics — a ClickHouse engine has nothing to do with JSON key-value storage.

`QueryEngine` replaces `Engine` as the contract DataAgents depend on. `SQLiteEngine` continues to implement all eight methods; persistence methods are simply no longer part of the ABC and are called directly where needed (models layer). `Engine` is removed.

### 2. `BaseDataAgent` extends `BaseAgent[DataModel]`, not a standalone class

`BaseDataAgent` inherits from `BaseAgent[DataModel]` — same pattern as `AnalystAgent`. This keeps usage tracking, system prompt assembly, and `UsageLimits` consistent across all agents without duplication.

`initialize()` is a separate async method (not called in `__init__`) because it does I/O: `list_tables()`, `get_schema()`, `get_sample(n=1)` per table. It is called once at server startup. If the backend is unreachable, `initialize()` raises — failing fast is preferable to discovering a dead data source mid-investigation.

`routing_description` is set by `initialize()`. Accessing `run()` before `initialize()` has been called raises `RuntimeError`.

### 3. Dynamic tool registration via factory function — deliberate exception to the "no closures" rule

PydanticAI uses the function's `__name__` as the tool name and `__doc__` as the description. Registering `query_auth_siem` and `query_network_siem` as distinct tools requires functions with those exact names — methods on `AnalystAgent` cannot have runtime-determined names.

A module-level factory function `_make_query_tool(agent: BaseDataAgent)` creates a typed async function, sets `__name__ = f"query_{agent.name}"` and `__doc__ = agent.routing_description`, then returns it. `AnalystAgent.__init__` loops over `data_agents` and calls `self.agent.tool_plain(_make_query_tool(agent))` for each.

This is a deliberate, scoped exception to the "no closures" rule: the factory is at module level (not inside a method), it is only used for dynamic registration, and the rationale is documented here. All other tools remain methods.

Tool name collisions (two agents with the same `name`) are validated in `AnalystAgent.__init__` with a clear `ValueError`.

### 4. `AnalystAgent` constraint updated to reference tools by pattern

Current constraint: `"Call query_data at most 2 times total"`. With dynamic tool names this becomes: `"Call each data source tool at most 2 times; stop querying as soon as you have sufficient evidence"`. The total request cap via `UsageLimits` remains the hard ceiling.

### 5. Orchestrator receives pre-initialized `data_agents` at construction

`Orchestrator.__init__` gains `data_agents: list[BaseDataAgent]`. These are created and `await agent.initialize()`'d in `create_app()` lifespan, before the server starts accepting requests. The Orchestrator passes them through to `AnalystAgent` at investigation time.

`DataAgent.create()` factory is removed. Construction becomes explicit at the call site.

## Risks / Trade-offs

**Startup latency** — `initialize()` samples each table at startup. For a SQLite dev DB this is negligible. For production backends (Elasticsearch with many data views) this could add a few seconds. → Acceptable: one-time cost, predictable, fails fast.

**`routing_description` in system prompt** — Each DataAgent's description is injected into `AnalystAgent`'s tool docstring and therefore sent to the LLM on every investigation. With many DataAgents this grows. → Mitigated by keeping descriptions compact (schema + 1 sample event per table, formatted concisely).

**PydanticAI tool registration contract** — Setting `__name__` and `__doc__` on dynamically created functions relies on PydanticAI reading those attributes, which is current behavior. Worth a targeted test to catch regressions on PydanticAI upgrades.

## Migration Plan

1. Extract `QueryEngine` ABC from `src/engines/base.py`; update `SQLiteEngine` to implement it; remove `Engine`
2. Update `DatabaseModel` imports to use `SQLiteEngine` directly (no ABC needed)
3. Add `BaseDataAgent` to `src/agents/data/base_data_agent.py`
4. Add `SQLiteDataAgent` to `src/agents/data/sqlite_data_agent.py` — port current `DataAgent` logic
5. Update `AnalystAgent` constructor to accept `data_agents: list[BaseDataAgent]`, add factory function, update constraints
6. Update `Orchestrator` to accept and forward `data_agents`
7. Update `create_app()` lifespan to construct and initialize `SQLiteDataAgent`, pass to `Orchestrator`
8. Remove `DataAgent` / `DataAgent.create()`; update all imports
9. Run full test suite — zero failures expected

No rollback plan needed: this is a pure refactor in a private repo. If tests fail, fix before merging.

## Open Questions

- Should `BaseDataAgent` live under `src/agents/data/` (new subdirectory) or stay flat in `src/agents/`? Subdirectory is cleaner as the number of DataAgent implementations grows.
- Should `SQLiteDataAgent` default `name` to `"sqlite"` or require it at construction? Requiring it explicitly makes the routing description more meaningful (e.g. `"security_logs"` instead of `"sqlite"`).
