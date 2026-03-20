import pytest
from pydantic_ai.models.test import TestModel

from src.agents.data_agent import DataAgent
from src.engines.sqlite import SQLiteEngine


@pytest.fixture
def data_agent(seeded_db):
    return DataAgent(model=TestModel(), engines=[SQLiteEngine(seeded_db)])
