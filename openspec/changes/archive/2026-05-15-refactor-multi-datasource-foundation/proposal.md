## Why

The current `DataAgent` treats all backends as a single unified query space — one agent, multiple engines, all schemas merged into one system prompt. This works for SQLite dev/test but breaks down when backends have different query languages (SQL vs ES|QL), different constraints, and different cost profiles. Adding Elasticsearch or ClickHouse as real data sources requires each backend to have its own agent with backend-specific instructions, constraints, and self-describing identity — so the AnalystAgent can route intelligently across multiple sources.

## What Changes

- `Engine` ABC is split: `QueryEngine` (list_tables, get_schema, get_sample, run_query) contains only query methods; persistence methods remain on `SQLiteEngine` directly, no longer part of the shared interface
- `BaseDataAgent` introduced: abstract base with `name: str`, `description: str`, `initialize() -> None` (introspects backend, builds routing description from schema + samples), and `run(request) -> DataModel`
- `SQLiteDataAgent` created as the concrete implementation wrapping current `DataAgent` logic — SQLite engine hardcoded, no behavior change
- Current `DataAgent` class removed or aliased to `SQLiteDataAgent` for backwards compatibility during transition
- `AnalystAgent` updated to accept `data_agents: list[BaseDataAgent]` instead of constructing a `DataAgent` internally; registers one `query_{agent.name}` tool per DataAgent at construction time, with each tool's docstring sourced from `agent.description`
- `AnalystAgent` constraint budget updated: per-source call limits derived from each DataAgent, plus an overall cap

## Capabilities

### New Capabilities
- `multi-datasource-routing`: AnalystAgent dynamically registers tools from a list of DataAgents and routes investigation queries by data domain, not by backend technology

### Modified Capabilities
- None — existing SQLite investigation path is preserved with identical behavior

## Impact

- `src/agents/data_agent.py` — refactored into `BaseDataAgent` + `SQLiteDataAgent`
- `src/agents/analyst_agent.py` — construction signature changes, dynamic tool registration
- `src/engines/base.py` — `QueryEngine` ABC extracted; `Engine` retained or removed
- `src/engines/sqlite.py` — persistence methods remain, now outside the shared ABC
- `src/config.py` — `DataAgent.create()` factory removed; construction moves to call sites
- No API changes, no schema changes, all existing tests must pass without modification
