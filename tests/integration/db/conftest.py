import pytest
from pydantic_ai.models.test import TestModel

from src.agents.data_sqlite_agent import DataSQLiteAgent

_DATA_AGENT_INSTRUCTIONS = (
    "You are a database expert. Use list_tables to discover available tables, "
    "get_schema to understand their structure, get_sample to preview data, "
    "and run_query to execute SQL queries. Always check schema before writing queries."
)


@pytest.fixture
def data_agent(seeded_db):
    return DataSQLiteAgent(
        model=TestModel(),
        instructions=_DATA_AGENT_INSTRUCTIONS,
        db_path=seeded_db,
    )
