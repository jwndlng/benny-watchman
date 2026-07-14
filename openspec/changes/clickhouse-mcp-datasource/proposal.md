## Why

Production log data lives in ClickHouse, reached over MCP stdio transport (per CLAUDE.md), whereas dev/test use SQLite and Elasticsearch in-process. Benny needs a ClickHouse data source that fits the existing DataAgent model without special-casing MCP.

Implements decision 6 of the `modular-soc-architecture` design.

## What Changes

- **A `QueryEngine` implementation over the ClickHouse MCP stdio client.** Benny acts as an MCP *client*; the client is wrapped as a `QueryEngine` so `capabilities/data` treats a ClickHouse-over-MCP source identically to the native SQLite/Elasticsearch backends. The DataAgent, its tools, and the routing pattern are reused unchanged.
- **Home in `mcp/clients/`.** The stdio client integration lives under `src/mcp/clients/` (established in slice 1); a `ClickHouseEngine` adapter bridges it into `src/engines/` and thus into `capabilities/data`.
- **Security boundary unchanged.** Read permissions are enforced at the ClickHouse user level, not via query parsing (per the project's design decisions).

## Capabilities

### New Capabilities
- `clickhouse-mcp-datasource`: a ClickHouse-backed `QueryEngine` + DataAgent that speaks to ClickHouse over the MCP stdio client

### Modified Capabilities
- None — the `QueryEngine` ABC and `BaseDataAgent` are reused as-is; this proves the abstraction holds for an MCP-backed source

## Impact

- **Depends on:** `modular-soc-architecture` slice 1 (`engines/` and `mcp/clients/` must exist). Independent of the module contract — it can proceed in parallel.
- `src/mcp/clients/clickhouse.py`: the stdio MCP client wrapper
- `src/engines/clickhouse.py`: a `ClickHouseEngine` implementing `QueryEngine` over that client (`list_tables`/`get_schema`/`get_sample`/`run_query`)
- `src/config.py`: ClickHouse connection settings (host, credentials), optional like the Elastic/Okta configs
- Enables the production data path; dev/test backends are untouched
