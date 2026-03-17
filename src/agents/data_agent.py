"""Translates natural language data requests into backend queries.

Receives requests from the AnalystAgent describing what data is needed.
Handles schema discovery, query construction, and execution against the
configured backend. Returns structured results.

DataAgent is a base class — backend-specific subclasses (DataSQLiteAgent, etc.)
own their connection lifecycle and implement the query tools.
"""

from abc import abstractmethod

from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent


class DataModel(BaseModel):
    rows: list[dict[str, object]] = Field(
        description="Rows retrieved matching the request"
    )
    notes: str = Field(description="What was queried and any relevant context")


class DataAgent(BaseAgent[DataModel]):
    @property
    def instructions(self) -> str:
        return (
            "You are a database expert. Use list_tables to discover available tables, "
            "get_schema to understand their structure, get_sample to preview data, "
            "and run_query to execute SQL queries. Always check schema before writing queries."
        )

    @property
    def constraints(self) -> list[str]:
        return [
            "Use at most 3 tool calls total",
            "Prefer targeted queries — avoid redundant schema lookups or broad scans",
            "Never use SELECT * — always name only the columns needed to answer the request",
            "Aggregate datasets using group by as much as possible to minimize the number of rows returned",
        ]

    @abstractmethod
    def list_tables(self): ...

    @abstractmethod
    def get_schema(self, table: str): ...

    @abstractmethod
    def get_sample(self, table: str, n: int = 5): ...

    @abstractmethod
    def run_query(self, sql: str): ...

    def __init__(self, model: str) -> None:
        super().__init__(model=model, output_type=DataModel, name="DataAgent")
        self.agent.tool_plain(self.list_tables)
        self.agent.tool_plain(self.get_schema)
        self.agent.tool_plain(self.get_sample)
        self.agent.tool_plain(self.run_query)

    @classmethod
    def create(cls, engine: str, model: str, **kwargs) -> "DataAgent":
        if engine == "sqlite":
            from src.agents.data_sqlite_agent import DataSQLiteAgent

            return DataSQLiteAgent(model=model, **kwargs)
        raise ValueError(f"Unknown data backend: {engine!r}")
