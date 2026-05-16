## Why

The system currently supports only SQLite as a query backend. To operate against a real Elastic SIEM deployment, benny needs an Elasticsearch data source — one that understands ES|QL query syntax, discovers available data through Kibana data views (the SOC team's curated index sets), and integrates cleanly with the multi-datasource foundation.

## What Changes

- `ElasticsearchEngine` implements `QueryEngine`:
  - `list_tables()` fetches Kibana data views via the Kibana API (not raw index listing) — returns one entry per data view, avoiding time-sharded index explosion
  - `get_schema()` returns field mappings from the data view's field listing
  - `get_sample()` returns a small number of real documents via ES|QL
  - `run_query()` executes ES|QL queries via the Elasticsearch ES|QL endpoint
  - No persistence methods — persistence stays on SQLite
- `ElasticDataAgent` extends `BaseDataAgent`:
  - Hardcodes `ElasticsearchEngine`
  - Instructions include ES|QL syntax guidance (pipe syntax, date math, no subqueries)
  - Constraints tuned for Elasticsearch cost profile
  - `initialize()` introspects data views and builds a routing description with field names and one sample event per data view
- Config additions: `ELASTIC_HOST`, `KIBANA_HOST`, `ELASTIC_API_KEY`
- Startup health check: `initialize()` fails fast if Elasticsearch or Kibana is unreachable

## Capabilities

### New Capabilities
- `elasticsearch-query-engine`: ES|QL query execution against Kibana data views
- `elastic-data-agent`: Self-describing Elasticsearch DataAgent with startup introspection

### Modified Capabilities
- None

## Impact

- `src/engines/elasticsearch.py` — new file
- `src/agents/data/elastic_data_agent.py` — new file
- `src/config.py` — new `ElasticConfig` with host, Kibana host, API key
- Requires `elasticsearch-py` dependency (official Python client)
- Requires Kibana connectivity at startup for data view discovery
- Depends on: `refactor-multi-datasource-foundation`
