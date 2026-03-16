"""Translates natural language data requests into backend queries.

Receives requests from the AnalystAgent describing what data is needed.
Handles schema discovery, query construction, and execution against the
configured backend. Returns structured results.

DataAgent is a base class — backend-specific subclasses (DataSQLiteAgent, etc.)
own their connection lifecycle and register tools as closures.
"""

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent


class DataModel(BaseModel):
    rows: list[dict] = Field(description="Rows retrieved matching the request")
    notes: str = Field(description="What was queried and any relevant context")


class DataAgent(BaseAgent[DataModel]):
    def __init__(self, model: str, instructions: str) -> None:
        super().__init__(model=model, output_type=DataModel, instructions=instructions)

    @classmethod
    def create(
        cls, engine: str, model: str, instructions: str, **kwargs
    ) -> "DataAgent":
        if engine == "sqlite":
            from src.agents.data_sqlite_agent import DataSQLiteAgent

            return DataSQLiteAgent(model=model, instructions=instructions, **kwargs)
        raise ValueError(f"Unknown data backend: {engine!r}")
