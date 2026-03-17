import pytest
from pydantic_ai.models.test import TestModel

from src.agents.data_sqlite_agent import DataSQLiteAgent


@pytest.fixture
def data_agent(seeded_db):
    return DataSQLiteAgent(model=TestModel(), db_path=seeded_db)
