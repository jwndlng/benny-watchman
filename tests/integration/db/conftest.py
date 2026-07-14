import pytest
from pydantic_ai.models.test import TestModel

from src.capabilities.data.sqlite_data_agent import SQLiteDataAgent


@pytest.fixture
def data_agent(seeded_db):
    # initialize() not called — tests exercise query tools directly, not run()
    return SQLiteDataAgent(name="test", model=TestModel(), db_path=seeded_db)
