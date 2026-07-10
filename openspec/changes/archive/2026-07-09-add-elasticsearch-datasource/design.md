## Context

benny-watchman currently supports only SQLite as a query backend via `SQLiteEngine` + `SQLiteDataAgent`. The `QueryEngine` ABC (`src/engines/base.py`) defines a synchronous interface: `list_tables`, `get_schema`, `get_sample`, `run_query`. SQLite's driver is synchronous and thread-safe, so the sync ABC fits.

Elasticsearch is the production target. All ES operations are HTTP calls. Using a synchronous Elasticsearch client would block the FastAPI event loop on every tool call during an investigation.

The `BaseDataAgent` pattern is established: a concrete subclass owns one engine, declares a name and routing description, and exposes tools registered via `tool_plain`. `initialize()` introspects the backend at startup and builds the routing description. `ElasticDataAgent` follows this pattern.

## Goals / Non-Goals

**Goals:**
- `ElasticsearchEngine`: async class wrapping `elasticsearch-py` AsyncElasticsearch client — `list_tables`, `get_schema`, `get_sample`, `run_query` all return coroutines
- `ElasticDataAgent`: subclass of `BaseDataAgent` with async tools and ES|QL-specific instructions and constraints
- Index discovery directly via the ES `_cat/indices` API — no Kibana dependency
- Config: `ELASTIC_HOST`, `ELASTIC_API_KEY` env vars under a new `_ElasticConfig`
- Fail fast at startup if Elasticsearch is unreachable

**Non-Goals:**
- Replacing or merging with `SQLiteDataAgent` — both can coexist
- Write operations (index, delete) — read-only
- ClickHouse integration — tracked separately
- Multi-tenant or per-user Elasticsearch credentials

## Decisions

### 1. `ElasticsearchEngine` does not inherit from `QueryEngine`

`QueryEngine` is a synchronous ABC. Extending it to support async would break `SQLiteEngine` and require a larger refactor. Wrapping async calls in `asyncio.to_thread` to conform to the sync interface adds indirection and wastes a thread per tool call.

**Decision:** `ElasticsearchEngine` is a standalone async class with the same method signatures as `QueryEngine` but declared `async def`. `ElasticDataAgent` tool methods are `async def` and call the engine directly — `tool_plain` accepts coroutines natively in PydanticAI.

**Alternative considered:** `asyncio.to_thread` adapter to preserve the `QueryEngine` contract. Rejected: adds complexity with no benefit since `ElasticDataAgent` owns its tools and the ABC provides no runtime polymorphism here.

### 2. Direct index listing via `_cat/indices` with optional index filter

**Decision:** `list_tables()` calls `GET /_cat/indices?format=json` on Elasticsearch. Each index name is returned as the "table name" and used directly in ES|QL `FROM` clauses. Field schema comes from `GET /{index}/_mapping`.

Production clusters contain many system indices (`.kibana`, `.security-*`, `.fleet-*`, etc.) that are irrelevant for security investigations. An optional `ELASTIC_INDEX_PATTERN` env var filters which indices are returned. When set, `_cat/indices/{pattern}` is called directly, so only matching indices are fetched — e.g. `logs-*` returns only log indices. When unset, all non-hidden indices are returned (indices not starting with `.`).

Time-sharded rollover indices (e.g. `logs-2025.05.01`) are common in Elastic SIEM deployments and will appear as individual entries. The agent can use wildcard patterns in ES|QL (`FROM logs-* | ...`) to query across them. The routing description in `initialize()` groups indices by base name prefix so the agent understands the landscape without a shard-per-line listing.

**Alternative considered:** Kibana data views. Deferred: adds a `KIBANA_HOST` dependency and Kibana API surface for no functional gain at this stage.

### 3. Reuse `ColumnInfo` for ES field metadata

`ColumnInfo` has `notnull` and `pk` fields which are meaningless for Elasticsearch. However, reusing it lets `schema_context()`-style formatting work without a new type, and the LLM ignores empty flag strings.

**Decision:** Use `ColumnInfo(name=..., type=..., notnull=False, pk=False)` for all ES fields. The `type` carries the ES field type (`keyword`, `date`, `long`, etc.).

**Alternative considered:** New `ESFieldInfo` model. Rejected: unnecessary abstraction — the two extra fields being `False` is harmless.

### 4. All ES calls via `AsyncElasticsearch`

**Decision:** The `elasticsearch-py[async]` client is used for all operations — index listing, mapping fetch, and ES|QL query execution. No `httpx` calls needed; the SDK covers everything.

Config is `ELASTIC_HOST` + `ELASTIC_API_KEY`. Optional `ELASTIC_INDEX_PATTERN` (default: unset → all non-hidden indices). No `KIBANA_HOST`.

### 6. ES|QL `run_query` with implicit LIMIT

ES|QL queries can return large result sets. Without a `LIMIT` clause, a query defaults to 1000 rows in ES|QL.

**Decision:** `run_query` appends `| LIMIT 500` when the query doesn't already contain a `LIMIT` pipe stage — same guard as `SQLiteEngine`. The agent is also constrained to avoid broad scans via `constraints`.

## Risks / Trade-offs

**Time-sharded index explosion** → SIEM deployments may have hundreds of rollover shards. Listing all of them verbatim in the routing description wastes tokens. Mitigation: `initialize()` groups indices by base name prefix (everything before the trailing date segment) and reports the group count rather than individual shards. The agent uses wildcard patterns in queries.

**ES|QL feature parity** → ES|QL lacks subqueries, CTEs, and window functions. Agents used to SQL may generate invalid queries. Mitigation: `instructions` includes explicit ES|QL syntax guidance and common pitfall warnings.

**`AsyncElasticsearch` connection lifecycle** → The client holds a persistent connection pool. In FastAPI, this should be closed on shutdown. Mitigation: `ElasticDataAgent` exposes a `close()` coroutine; `app.py` wires it to FastAPI's `lifespan` shutdown hook.

## Migration Plan

1. Add `elasticsearch-py[async]>=8.0` to `pyproject.toml`
2. Implement `src/engines/elasticsearch.py`
3. Implement `src/agents/data/elastic_data_agent.py`
4. Add `_ElasticConfig` + `_load_elastic_config()` to `src/config.py`
5. Wire up in `src/api/app.py`: construct `ElasticDataAgent` when `cfg.elastic` is set, pass to `Orchestrator` alongside existing data agents
6. Add `ELASTIC_HOST`, `ELASTIC_API_KEY`, `ELASTIC_INDEX_PATTERN` to `.env.example`
7. Add unit tests for engine and agent

**Rollback:** If `cfg.elastic` is `None` (env vars absent), the Elasticsearch path is never constructed. SQLite remains the active backend. No config change needed to revert to SQLite-only.

## Open Questions

- **Index grouping heuristic:** The prefix-based grouping (strip trailing date segment) covers `logs-2025.05.01` patterns but may misgroup indices with numeric suffixes that aren't dates. Good enough for now?
- **ES cluster version:** Minimum ES version to target? ES|QL requires ≥8.11. Should `initialize()` log a warning if the cluster version is too old?
