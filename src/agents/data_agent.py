"""Translates natural language data requests into backend queries.

Receives requests from the AnalystAgent describing what data is needed.
Delegates all data access to a list of Engine instances — one per backend source.
Schema from all engines is pre-loaded into the system prompt so the agent
knows what data is available without spending tool calls on discovery.
"""

from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent
from src.engines.base import ColumnInfo, Engine, TableInfo


class DataModel(BaseModel):
    rows: list[dict[str, object]] = Field(
        description="Rows retrieved matching the request"
    )
    notes: str = Field(description="What was queried and any relevant context")


class DataAgent(BaseAgent[DataModel]):
    @property
    def instructions(self) -> str:
        schema = "".join(e.schema_context() for e in self._engines)
        return (
            "You are a database expert. Use list_tables to discover available tables, "
            "get_schema to understand their structure, get_sample to preview data, "
            "and run_query to execute SQL queries. Always check schema before writing queries."
            + schema
        )

    @property
    def constraints(self) -> list[str]:
        return [
            "Use at most 3 tool calls total",
            "Prefer targeted queries — avoid redundant schema lookups or broad scans",
            "Never use SELECT * — always name only the columns needed to answer the request",
            "Aggregate datasets using group by as much as possible to minimize the number of rows returned",
        ]

    def __init__(self, model: str, engines: list[Engine]) -> None:
        self._engines = (
            engines  # must be set before super().__init__ calls self.instructions
        )
        super().__init__(model=model, output_type=DataModel, name="DataAgent")
        self.agent.tool_plain(self.list_tables)
        self.agent.tool_plain(self.get_schema)
        self.agent.tool_plain(self.get_sample)
        self.agent.tool_plain(self.run_query)

    def _engine_for(self, table: str) -> Engine:
        """Return the first engine that contains the given table, or the primary engine."""
        for engine in self._engines:
            if any(t.name == table for t in engine.list_tables()):
                return engine
        return self._engines[0]

    def list_tables(self) -> list[TableInfo]:
        """Return all table names available across all backends."""
        tables: list[TableInfo] = []
        for engine in self._engines:
            tables.extend(engine.list_tables())
        return tables

    def get_schema(self, table: str) -> list[ColumnInfo]:
        """Return column names, types, and constraints for the given table."""
        return self._engine_for(table).get_schema(table)

    def get_sample(self, table: str, n: int = 5) -> list[dict[str, object]]:
        """Return n sample rows from the table to understand its structure and values."""
        return self._engine_for(table).get_sample(table, n)

    def run_query(self, sql: str) -> list[dict[str, object]]:
        """Execute a read-only SELECT query and return matching rows.
        Use only columns you need — never SELECT *. Single statement only."""
        return self._engines[0].run_query(sql)

    @classmethod
    def create(cls, engine: str, model: str, **kwargs) -> "DataAgent":
        """Instantiate a DataAgent wired to the named backend engine."""
        if engine == "sqlite":
            from src.engines.sqlite import SQLiteEngine

            return cls(model=model, engines=[SQLiteEngine(kwargs["db_path"])])
        raise ValueError(f"Unknown data backend: {engine!r}")
