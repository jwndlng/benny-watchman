"""Translates natural language data requests into backend queries.

Receives requests from the AnalystAgent describing what data is needed.
Handles schema discovery, query construction, and execution against the
configured backend (Clickhouse, etc.). Returns structured results.
"""

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent


class DataModel(BaseModel):
    query: str = Field(description="The query that was executed")
    rows: list[dict] = Field(description="Rows returned from the backend")


class DataAgent(BaseAgent[DataModel]):
    def __init__(self, model: str, instructions: str) -> None:
        super().__init__(model=model, output_type=DataModel, instructions=instructions)
