"""Elasticsearch async query engine."""

from __future__ import annotations

import asyncio
import re

import logfire
from elasticsearch import Elasticsearch, TransportError

from src.engines.base import ColumnInfo, TableInfo


def _rows_from_esql(response: object) -> list[dict[str, object]]:
    r = response  # type: ignore[union-attr]
    columns = [col["name"] for col in r.get("columns", [])]
    return [dict(zip(columns, row)) for row in r.get("values", [])]


class ElasticsearchEngine:
    """Elasticsearch query engine.

    Uses the sync Elasticsearch client via asyncio.to_thread to avoid aiohttp
    compatibility issues on Python 3.14. Does not inherit from the sync QueryEngine
    ABC — all public methods are async from the caller's perspective.
    """

    def __init__(
        self,
        host: str,
        api_key: str,
        index_pattern: str | None = None,
    ) -> None:
        self._client = Elasticsearch(hosts=[host], api_key=api_key)
        self._index_pattern = index_pattern

    async def list_tables(self) -> list[TableInfo]:
        """Return index names matching the configured filter as TableInfo entries.

        Uses _field_caps (requires only read privilege) to discover indices.
        Falls back to _cat/indices when field_caps returns no data.
        """
        pattern = self._index_pattern or "*"

        def _fetch() -> list[str]:
            try:
                response = self._client.field_caps(
                    index=pattern,
                    fields=["@timestamp", "_id"],
                    include_unmapped=False,
                )
                raw: list[str] = list(response.get("indices", []))
            except TransportError:
                cat_response = self._client.cat.indices(
                    index=pattern, format="json", h="index"
                )
                raw = [r["index"] for r in cat_response]
            if not self._index_pattern:
                raw = [i for i in raw if not i.startswith(".")]
            return sorted(set(raw))

        indices = await asyncio.to_thread(_fetch)
        return [TableInfo(name=idx) for idx in indices]

    async def get_schema(self, index: str) -> list[ColumnInfo]:
        """Return field info for an index as ColumnInfo entries.

        Uses _field_caps (requires only read privilege). Accepts wildcard patterns.
        notnull and pk are always False (not applicable to Elasticsearch fields).
        """

        def _fetch() -> list[ColumnInfo]:
            response = self._client.field_caps(
                index=index,
                fields=["*"],
                include_unmapped=False,
            )
            fields: dict[str, dict[str, object]] = response.get("fields", {})  # type: ignore[assignment]
            result = []
            for name, type_map in fields.items():
                field_type = next(iter(type_map.keys()), "object")
                result.append(
                    ColumnInfo(name=name, type=field_type, notnull=False, pk=False)
                )
            return sorted(result, key=lambda c: c.name)

        return await asyncio.to_thread(_fetch)

    @logfire.instrument("es_get_sample")
    async def get_sample(self, index: str, n: int = 5) -> list[dict[str, object]]:
        """Return up to n documents from an index via ES|QL."""

        def _fetch() -> list[dict[str, object]]:
            response = self._client.esql.query(
                body={"query": f"FROM {index} | LIMIT {n}"}
            )
            return _rows_from_esql(response)

        return await asyncio.to_thread(_fetch)

    @logfire.instrument("es_run_query")
    async def run_query(self, esql: str) -> list[dict[str, object]]:
        """Execute an ES|QL query and return results as a list of dicts.

        Appends | LIMIT 500 when the query does not already contain a LIMIT pipe stage.
        """
        if not re.search(r"\|\s*limit\b", esql, re.IGNORECASE):
            esql = esql.rstrip() + " | LIMIT 500"

        def _fetch(q: str) -> list[dict[str, object]]:
            response = self._client.esql.query(body={"query": q})
            logfire.info(
                "es_run_query result", row_count=len(response.get("values", []))
            )  # type: ignore[union-attr]
            return _rows_from_esql(response)

        return await asyncio.to_thread(_fetch, esql)

    async def close(self) -> None:
        """Close the underlying Elasticsearch connection pool."""
        await asyncio.to_thread(self._client.close)
