## ADDED Requirements

### Requirement: List available indices
The engine SHALL return all indices matching the configured filter when `list_tables()` is called. Each index is returned as a `TableInfo` with its name as the table identifier used in ES|QL `FROM` clauses. When `ELASTIC_INDEX_PATTERN` is set, only indices matching the glob pattern are returned. When unset, all non-hidden indices (those not starting with `.`) are returned.

#### Scenario: Pattern filter applied
- **WHEN** `ELASTIC_INDEX_PATTERN` is set to `logs-*`
- **THEN** only indices whose names match `logs-*` are returned

#### Scenario: No filter configured
- **WHEN** `ELASTIC_INDEX_PATTERN` is not set
- **THEN** all indices not starting with `.` are returned

#### Scenario: Elasticsearch unreachable
- **WHEN** `list_tables()` is called and the cluster is unreachable
- **THEN** an exception is raised with a descriptive message

### Requirement: Return field schema for an index
The engine SHALL return the field mappings for a named index when `get_schema()` is called. Each field is returned as a `ColumnInfo` with its name and ES field type (e.g. `keyword`, `date`, `long`). The `notnull` and `pk` fields SHALL be `False` for all ES fields.

#### Scenario: Schema for existing index
- **WHEN** `get_schema("logs-2025.05.01")` is called
- **THEN** a list of `ColumnInfo` objects is returned, one per mapped field

#### Scenario: Unknown index
- **WHEN** `get_schema()` is called with an index that does not exist
- **THEN** an exception is raised

### Requirement: Return sample documents
The engine SHALL return up to `n` documents from an index when `get_sample()` is called, using an ES|QL `FROM <index> | LIMIT <n>` query.

#### Scenario: Sample from populated index
- **WHEN** `get_sample("logs-*", n=3)` is called
- **THEN** at most 3 documents are returned as dicts

#### Scenario: Empty index
- **WHEN** `get_sample()` is called on an index with no documents
- **THEN** an empty list is returned

### Requirement: Execute ES|QL queries
The engine SHALL execute ES|QL queries when `run_query()` is called and return results as a list of dicts. Queries that do not contain a `LIMIT` pipe stage SHALL have `| LIMIT 500` appended automatically. Only read operations are permitted.

#### Scenario: Query without LIMIT
- **WHEN** `run_query("FROM logs-* | WHERE event.category == \"authentication\"")` is called
- **THEN** `| LIMIT 500` is appended and the query executes successfully

#### Scenario: Query with explicit LIMIT
- **WHEN** the query already contains `| LIMIT 100`
- **THEN** the query is executed as-is without modification

#### Scenario: Query returns results
- **WHEN** a valid ES|QL query is executed
- **THEN** each result row is returned as a `dict[str, object]`

### Requirement: Close client connection
The engine SHALL expose a `close()` coroutine that closes the underlying `AsyncElasticsearch` connection pool.

#### Scenario: Graceful shutdown
- **WHEN** `await engine.close()` is called
- **THEN** the Elasticsearch connection pool is closed without error
