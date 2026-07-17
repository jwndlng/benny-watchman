"""Unit tests for BaseDataAgent and AnalystAgent multi-datasource wiring."""

import pytest
from pydantic_ai.models.test import TestModel

from src.capabilities.subagents.data.sqlite_data_agent import SQLiteDataAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _initialized_agent(db_path: str, name: str = "test_source") -> SQLiteDataAgent:
    """Return a SQLiteDataAgent with routing_description pre-set (no I/O needed)."""
    agent = SQLiteDataAgent(name=name, model=TestModel(), db_path=db_path)
    agent._routing_description = f"Source '{name}' with synthetic data."
    return agent


# ---------------------------------------------------------------------------
# BaseDataAgent: uninitialized guard
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_run_before_initialize_raises(seeded_db):
    agent = SQLiteDataAgent(name="test_source", model=TestModel(), db_path=seeded_db)
    with pytest.raises(RuntimeError, match="not been initialized"):
        await agent.run("find all events")


def test_routing_description_before_initialize_raises(seeded_db):
    agent = SQLiteDataAgent(name="test_source", model=TestModel(), db_path=seeded_db)
    with pytest.raises(RuntimeError, match="not been initialized"):
        _ = agent.routing_description


# ---------------------------------------------------------------------------
# SQLiteDataAgent: initialize() builds routing_description
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_initialize_builds_routing_description(seeded_db):
    agent = SQLiteDataAgent(name="test_source", model=TestModel(), db_path=seeded_db)
    await agent.initialize()
    assert "test_source" in agent.routing_description
    assert "auth_logs" in agent.routing_description


# ---------------------------------------------------------------------------
# AnalystAgent: dynamic tool registration
# ---------------------------------------------------------------------------


def test_single_data_agent_registers_query_tool(seeded_db):
    from src.modules.siem.analyst import AnalystAgent

    analyst = AnalystAgent(
        model=TestModel(),
        data_agents=[_initialized_agent(seeded_db)],
    )
    assert "query_test_source" in analyst.agent._function_toolset.tools


def test_multiple_data_agents_register_separate_tools(seeded_db, tmp_path):
    from src.modules.siem.analyst import AnalystAgent

    db2 = str(tmp_path / "second.db")
    agent_b = SQLiteDataAgent(name="network_siem", model=TestModel(), db_path=db2)
    agent_b._routing_description = "Network siem source."

    analyst = AnalystAgent(
        model=TestModel(),
        data_agents=[
            _initialized_agent(seeded_db, name="auth_siem"),
            agent_b,
        ],
    )
    tools = analyst.agent._function_toolset.tools
    assert "query_auth_siem" in tools
    assert "query_network_siem" in tools


# ---------------------------------------------------------------------------
# AnalystAgent: duplicate name rejection
# ---------------------------------------------------------------------------


def test_duplicate_data_agent_names_raise(seeded_db):
    from src.modules.siem.analyst import AnalystAgent

    with pytest.raises(ValueError, match="Duplicate DataAgent names"):
        AnalystAgent(
            model=TestModel(),
            data_agents=[
                _initialized_agent(seeded_db, name="same"),
                _initialized_agent(seeded_db, name="same"),
            ],
        )
