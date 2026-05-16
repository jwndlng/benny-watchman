"""SQLite-backed data retrieval agent for dev and test environments."""

import json

import logfire

from src.agents.data.base_data_agent import BaseDataAgent, DataModel
from src.engines.base import ColumnInfo, TableInfo
from src.engines.sqlite import SQLiteEngine


class SQLiteDataAgent(BaseDataAgent):
    """SQLite-backed data retrieval agent for dev and test environments."""

    @property
    def instructions(self) -> str:
        return (
            "You are a database expert. Use list_tables to discover available tables, "
            "get_schema to understand their structure, get_sample to preview data, "
            "and run_query to execute SQL queries. Always check schema before writing queries."
            + self._engine.schema_context()
        )

    @property
    def constraints(self) -> list[str]:
        return [
            "Use at most 3 tool calls total",
            "Prefer targeted queries — avoid redundant schema lookups or broad scans",
            "Never use SELECT * — always name only the columns needed to answer the request",
            "Aggregate with GROUP BY to minimize rows returned",
        ]

    def __init__(self, name: str, model: str, db_path: str) -> None:
        self._name = name
        self._routing_description = None
        self._engine = SQLiteEngine(db_path)
        super().__init__(
            model=model,
            output_type=DataModel,
            name=f"SQLiteDataAgent({name})",
        )
        self.agent.tool_plain(self.list_tables)
        self.agent.tool_plain(self.get_schema)
        self.agent.tool_plain(self.get_sample)
        self.agent.tool_plain(self.run_query)

    async def initialize(self) -> None:
        """Introspect the SQLite DB and build a compact routing description."""
        tables = self._engine.list_tables()
        if not tables:
            self._routing_description = (
                f"SQLite source '{self._name}': no tables found."
            )
            return
        parts: list[str] = [f"SQLite data source '{self._name}'."]
        for table in tables:
            schema = self._engine.get_schema(table.name)
            sample = self._engine.get_sample(table.name, n=1)
            field_names = ", ".join(c.name for c in schema)
            sample_str = json.dumps(sample[0]) if sample else "(empty)"
            parts.append(
                f"Table: {table.name}\n  Fields: {field_names}\n  Sample: {sample_str}"
            )
        self._routing_description = "\n\n".join(parts)
        logfire.info("SQLiteDataAgent initialized", name=self._name, tables=len(tables))

    def list_tables(self) -> list[TableInfo]:
        """Return all table names available in the database."""
        return self._engine.list_tables()

    def get_schema(self, table: str) -> list[ColumnInfo]:
        """Return column names, types, and constraints for the given table."""
        return self._engine.get_schema(table)

    def get_sample(self, table: str, n: int = 5) -> list[dict[str, object]]:
        """Return n sample rows from the table to understand its structure and values."""
        return self._engine.get_sample(table, n)

    def run_query(self, sql: str) -> list[dict[str, object]]:
        """Execute a read-only SQLite SELECT query and return matching rows.
        Use only columns you need — never SELECT *. Single statement only."""
        return self._engine.run_query(sql)
