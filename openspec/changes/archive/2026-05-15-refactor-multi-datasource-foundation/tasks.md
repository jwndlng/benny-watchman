## 1. Engine ABC

- [x] 1.1 Extract `QueryEngine` ABC in `src/engines/base.py` with only the four query methods (`list_tables`, `get_schema`, `get_sample`, `run_query`); remove persistence methods from the ABC; delete or keep `Engine` as a deprecated alias temporarily
- [x] 1.2 Update `SQLiteEngine` to extend `QueryEngine`; persistence methods (`init_store`, `upsert`, `fetch`, `fetch_all`) remain on the class but are no longer part of the ABC contract
- [x] 1.3 Update `src/models.py` — `ModelFactory` and `DatabaseModel` reference `SQLiteEngine` directly, removing the `Engine` type hint

## 2. BaseDataAgent + SQLiteDataAgent

- [x] 2.1 Create `src/agents/data/` package with `__init__.py`
- [x] 2.2 Implement `BaseDataAgent` in `src/agents/data/base_data_agent.py`: `name: str` property, `routing_description: str` property that raises `RuntimeError` before `initialize()` completes, abstract `initialize() -> None`, and `run(request: str) -> DataModel` that guards against uninitialized state
- [x] 2.3 Implement `SQLiteDataAgent` in `src/agents/data/sqlite_data_agent.py`: hardcode `SQLiteEngine`, port `list_tables`, `get_schema`, `get_sample`, `run_query` tools from current `DataAgent`; implement `initialize()` that calls `list_tables()`, `get_schema()`, `get_sample(n=1)` per table and builds a formatted `routing_description`

## 3. AnalystAgent

- [x] 3.1 Add module-level `_make_query_tool(agent: BaseDataAgent)` factory in `src/agents/analyst_agent.py` that returns an async function with `__name__ = f"query_{agent.name}"` and `__doc__ = agent.routing_description`
- [x] 3.2 Update `AnalystAgent.__init__` to accept `data_agents: list[BaseDataAgent]`; validate name uniqueness (raise `ValueError` on duplicates); register each via `self.agent.tool_plain(_make_query_tool(a))`
- [x] 3.3 Remove the `_data_agent` field and internal `DataAgent` construction from `AnalystAgent.__init__`
- [x] 3.4 Update `AnalystAgent.constraints` to reference data source tools generically (replace the `query_data` references)

## 4. Orchestrator + App Wiring

- [x] 4.1 Add `data_agents: list[BaseDataAgent]` to `Orchestrator.__init__`; forward to `AnalystAgent(data_agents=self._data_agents)` inside `investigate()`
- [x] 4.2 Update `create_app()` lifespan in `src/api/app.py`: construct `SQLiteDataAgent` with `name` and `db_path` from config, call `await agent.initialize()`, pass to `Orchestrator`
- [x] 4.3 Add `DATA_AGENT_NAME` env var to `_DataConfig` in `src/config.py` (default: `"security_logs"`) so the SQLiteDataAgent has a meaningful tool name

## 5. Cleanup + Verification

- [x] 5.1 Delete `src/agents/data_agent.py`; update all imports across `src/` and `tests/` that reference `DataAgent` or `DataAgent.create()`
- [x] 5.2 Add unit tests in `tests/unittests/agents/` for: `run()` before `initialize()` raises `RuntimeError`; duplicate DataAgent names in `AnalystAgent` raise `ValueError`; tool name registered as `query_{name}` matches expected pattern
- [x] 5.3 Run `make test` and confirm zero failures
