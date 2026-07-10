# Spec: ElasticDataAgent

## Purpose

The `ElasticDataAgent` is a PydanticAI-based data agent that wraps `ElasticsearchEngine` and exposes it to the `Orchestrator` as a queryable data source. It introspects the Elasticsearch cluster at startup to build a routing description, provides ES|QL-aware instructions to the LLM, and manages the lifecycle of the underlying connection pool.

## Requirements

### Requirement: Initialize with index introspection
The agent SHALL introspect the Elasticsearch cluster during `initialize()` and build a routing description. The routing description SHALL group time-sharded indices by base name prefix, include field names for a representative index in each group, and include one sample document per group. `initialize()` SHALL raise if Elasticsearch is unreachable so that startup fails fast.

#### Scenario: Successful initialization
- **WHEN** `initialize()` is called and Elasticsearch is reachable
- **THEN** `routing_description` is set and includes index group names and a sample of their fields

#### Scenario: Indices grouped by prefix
- **WHEN** the cluster contains `logs-2025.05.01`, `logs-2025.05.02`, and `audit-2025.05.01`
- **THEN** the routing description reflects two groups: `logs-*` and `audit-*`, not three individual indices

#### Scenario: Elasticsearch unreachable at startup
- **WHEN** `initialize()` is called and Elasticsearch is unreachable
- **THEN** an exception is raised

#### Scenario: No matching indices
- **WHEN** `initialize()` completes with zero matching indices
- **THEN** `routing_description` is set to a message indicating no indices were found (no exception raised)

### Requirement: Expose ES|QL-aware instructions
The agent's `instructions` property SHALL describe the agent as an Elasticsearch query expert and include ES|QL syntax guidance: pipe syntax (`FROM ... | WHERE ... | STATS ...`), date math, available aggregations, and the constraint that subqueries and CTEs are not supported.

#### Scenario: Instructions include ES|QL guidance
- **WHEN** `agent.instructions` is accessed
- **THEN** the returned string contains ES|QL pipe syntax examples and notes about unsupported SQL features

### Requirement: Constrain tool call budget
The agent's `constraints` SHALL limit the agent to a maximum of 3 tool calls per run, discourage `SELECT *`-equivalent broad queries, and require `LIMIT` in all queries.

#### Scenario: Constraints injected into system prompt
- **WHEN** `agent.system_prompt` is accessed
- **THEN** the returned string includes the tool call budget and query discipline constraints

### Requirement: Close underlying engine connection
The agent SHALL expose a `close()` coroutine that closes the `ElasticsearchEngine` connection pool.

#### Scenario: Graceful shutdown
- **WHEN** `await agent.close()` is called
- **THEN** the underlying engine's `close()` is awaited without error

### Requirement: Wire into app lifecycle
The `ElasticDataAgent` SHALL be constructed in `app.py` when `cfg.elastic` is not `None`, registered with `Orchestrator` as a data agent, and closed during FastAPI's shutdown lifespan event.

#### Scenario: Agent created when config present
- **WHEN** `ELASTIC_HOST` and `ELASTIC_API_KEY` are set
- **THEN** an `ElasticDataAgent` is constructed, initialized, and passed to `Orchestrator`

#### Scenario: Agent skipped when config absent
- **WHEN** `ELASTIC_HOST` or `ELASTIC_API_KEY` is missing
- **THEN** no `ElasticDataAgent` is created and the app starts with only the configured data agents
