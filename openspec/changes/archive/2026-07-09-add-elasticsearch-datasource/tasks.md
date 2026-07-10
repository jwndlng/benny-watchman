## 1. Dependencies & Config

- [x] 1.1 Add `elasticsearch-py[async]>=8.0` to `pyproject.toml` and run `uv lock`
- [x] 1.2 Add `_ElasticConfig` dataclass and `_load_elastic_config()` to `src/config.py` — reads `ELASTIC_HOST`, `ELASTIC_API_KEY`, optional `ELASTIC_INDEX_PATTERN`
- [x] 1.3 Expose `config.elastic: _ElasticConfig | None` on the `Config` class
- [x] 1.4 Add `ELASTIC_HOST`, `ELASTIC_API_KEY`, `ELASTIC_INDEX_PATTERN` entries to `.env.example`

## 2. ElasticsearchEngine

- [x] 2.1 Create `src/engines/elasticsearch.py` with `ElasticsearchEngine` class backed by `AsyncElasticsearch`
- [x] 2.2 Implement `__init__(host, api_key, index_pattern=None)` — constructs `AsyncElasticsearch` with API key auth
- [x] 2.3 Implement `async list_tables()` — calls `_cat/indices/{pattern}` (or all non-hidden indices when pattern is unset), returns `list[TableInfo]`
- [x] 2.4 Implement `async get_schema(index)` — calls index mapping API, returns `list[ColumnInfo]` with `notnull=False, pk=False`
- [x] 2.5 Implement `async get_sample(index, n=5)` — runs `FROM <index> | LIMIT <n>` ES|QL query, returns `list[dict]`
- [x] 2.6 Implement `async run_query(esql)` — executes ES|QL, appends `| LIMIT 500` when no `LIMIT` pipe stage present, returns `list[dict]`
- [x] 2.7 Implement `async close()` — closes `AsyncElasticsearch` connection pool

## 3. ElasticDataAgent

- [x] 3.1 Create `src/agents/data/elastic_data_agent.py` with `ElasticDataAgent(BaseDataAgent)`
- [x] 3.2 Implement `__init__(name, model, host, api_key, index_pattern=None)` — constructs `ElasticsearchEngine`, sets `self._name` and `self._routing_description = None`, registers async tool methods via `tool_plain`
- [x] 3.3 Implement `instructions` property — describes the agent as an Elasticsearch query expert with ES|QL syntax guidance (pipe syntax, date math, no subqueries/CTEs)
- [x] 3.4 Implement `constraints` property — max 3 tool calls, always use `LIMIT`, avoid broad scans
- [x] 3.5 Implement `async initialize()` — calls `list_tables()`, groups time-sharded indices by base name prefix, fetches schema and one sample per group, builds `self._routing_description`; raises on connection failure
- [x] 3.6 Implement async tool methods: `list_tables`, `get_schema`, `get_sample`, `run_query` — thin delegates to engine
- [x] 3.7 Implement `async close()` — delegates to `self._engine.close()`

## 4. App Wiring

- [x] 4.1 In `app.py` lifespan, conditionally construct `ElasticDataAgent` when `cfg.elastic is not None` and append to the `data_agents` list passed to `Orchestrator`
- [x] 4.2 Await `elastic_data_agent.initialize()` at startup (inside lifespan, before `yield`)
- [x] 4.3 Await `elastic_data_agent.close()` at shutdown (inside lifespan, after `yield`)

## 5. Tests

- [x] 5.1 Add unit tests for `_load_elastic_config()` in `tests/unittests/test_config.py` — present/absent env vars
- [x] 5.2 Add `tests/unittests/engines/test_elasticsearch.py` — mock `AsyncElasticsearch`; test `list_tables` with and without pattern, `get_schema`, `get_sample`, `run_query` auto-LIMIT, `close`
- [x] 5.3 Add `tests/unittests/agents/test_elastic_data_agent.py` — test `initialize` index grouping logic, routing description content, and `close` delegation
