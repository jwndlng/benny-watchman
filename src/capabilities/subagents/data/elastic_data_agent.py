"""Elasticsearch-backed data retrieval agent."""

from __future__ import annotations

import json
import re

import logfire

from src.capabilities.subagents.data.base_data_agent import BaseDataAgent, DataModel
from src.core.ports.query_engine import ColumnInfo, TableInfo
from src.adapters.engines.elasticsearch import ElasticsearchEngine


def _index_prefix(name: str) -> str:
    """Strip trailing date-like segment for grouping rollover indices.

    e.g. logs-2025.05.01 → logs, audit-2025.05 → audit, myindex → myindex
    """
    stripped = re.sub(r"[-._]\d{4}[.\-]\d{2}([.\-]\d{2})?$", "", name)
    return stripped or name


class ElasticDataAgent(BaseDataAgent):
    """Elasticsearch-backed data retrieval agent with ES|QL query support."""

    @property
    def instructions(self) -> str:
        return (
            "You are an Elasticsearch query expert. Use list_tables to discover available "
            "indices, get_schema to understand their field mappings, get_sample to preview "
            "documents, and run_query to execute ES|QL queries. Always check the schema "
            "before writing queries.\n\n"
            "ES|QL syntax guide:\n"
            "- Pipe syntax: FROM <index> | WHERE <condition> | STATS <agg> BY <field>\n"
            "- Wildcard index patterns: FROM logs-* | ...\n"
            "- Date filtering: WHERE @timestamp >= NOW() - 24h\n"
            "- Aggregations: STATS count = COUNT(*), unique = COUNT_DISTINCT(user.name)\n"
            "- Sorting: | SORT @timestamp DESC\n"
            "- Always end queries with | LIMIT <n>\n\n"
            "ES|QL does NOT support: subqueries, CTEs, JOINs across indices, "
            "or window functions.\n\n"
            "After executing queries, return your final answer as a DataModel: "
            "set `rows` to the list of result documents from run_query, and `notes` "
            "to a brief summary of what index was queried and what was found."
        )

    @property
    def constraints(self) -> list[str]:
        return [
            "Use at most 3 tool calls total",
            "Always include LIMIT in every query — never return unbounded result sets",
            "Prefer targeted queries — avoid broad scans across all fields",
            "Use wildcard index patterns (e.g. logs-*) to query across rollover shards",
        ]

    def __init__(
        self,
        name: str,
        model: str,
        host: str,
        api_key: str,
        index_pattern: str | None = None,
    ) -> None:
        self._name = name
        self._routing_description = None
        self._engine = ElasticsearchEngine(
            host=host, api_key=api_key, index_pattern=index_pattern
        )
        super().__init__(
            model=model,
            output_type=DataModel,
            name=f"ElasticDataAgent({name})",
        )
        self.agent.tool_plain(self.list_tables)
        self.agent.tool_plain(self.get_schema)
        self.agent.tool_plain(self.get_sample)
        self.agent.tool_plain(self.run_query)

    async def initialize(self) -> None:
        """Introspect Elasticsearch indices and build a compact routing description.

        Groups time-sharded rollover indices by base name prefix. Makes exactly
        3 HTTP calls total (list, schema, sample) regardless of index count.
        Raises on connection failure so the app fails fast at startup.
        """
        tables = await self._engine.list_tables()
        if not tables:
            self._routing_description = (
                f"Elasticsearch source '{self._name}': no indices found."
            )
            return

        # Group by prefix — determines which patterns the agent should use in queries
        groups: dict[str, list[str]] = {}
        for t in tables:
            prefix = _index_prefix(t.name)
            groups.setdefault(prefix, []).append(t.name)

        # Single schema call over the full pattern (not per-group)
        full_pattern = self._engine._index_pattern or ",".join(
            sorted({_index_prefix(t.name) for t in tables})
        )
        try:
            schema = await self._engine.get_schema(full_pattern)
            field_names = ", ".join(c.name for c in schema[:50])
        except Exception:
            field_names = "(schema unavailable)"

        # Single sample call over the full pattern
        try:
            sample = await self._engine.get_sample(full_pattern, n=1)
            sample_str = json.dumps(sample[0]) if sample else "(empty)"
        except Exception:
            sample_str = "(sample unavailable)"

        # Build routing description: group summary + shared fields + sample
        group_lines = []
        for prefix, indices in sorted(groups.items()):
            if len(indices) > 1:
                group_lines.append(f"  {prefix}-* ({len(indices)} shards)")
            else:
                group_lines.append(f"  {indices[0]}")

        parts = [
            f"Elasticsearch data source '{self._name}'. "
            f"{len(tables)} indices across {len(groups)} groups.",
            "Available index groups (use as FROM patterns):\n" + "\n".join(group_lines),
            f"Common fields (sample from {full_pattern}):\n  {field_names}",
            f"Sample document:\n  {sample_str}",
        ]
        self._routing_description = "\n\n".join(parts)
        logfire.info(
            "ElasticDataAgent initialized", name=self._name, groups=len(groups)
        )

    async def list_tables(self) -> list[TableInfo]:
        """Return all Elasticsearch index names available for querying."""
        return await self._engine.list_tables()

    async def get_schema(self, index: str) -> list[ColumnInfo]:
        """Return field mappings for an index. Accepts wildcard patterns (e.g. logs-*)."""
        return await self._engine.get_schema(index)

    async def get_sample(self, index: str, n: int = 5) -> list[dict[str, object]]:
        """Return up to n documents from an index to understand its structure and values."""
        return await self._engine.get_sample(index, n)

    async def run_query(self, esql: str) -> list[dict[str, object]]:
        """Execute an ES|QL query and return matching documents.

        Use pipe syntax: FROM <index> | WHERE <condition> | STATS ... | LIMIT <n>
        Always name the fields you need — never retrieve all fields.
        LIMIT is required. Single query only (no semicolons).
        """
        return await self._engine.run_query(esql)

    async def close(self) -> None:
        """Close the underlying Elasticsearch connection pool."""
        await self._engine.close()
