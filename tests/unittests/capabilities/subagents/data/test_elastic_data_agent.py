"""Unit tests for ElasticDataAgent."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from src.capabilities.subagents.data.elastic_data_agent import (
    ElasticDataAgent,
    _index_prefix,
)
from src.core.ports.query_engine import ColumnInfo, TableInfo


# ---------------------------------------------------------------------------
# _index_prefix helper
# ---------------------------------------------------------------------------


def test_prefix_strips_daily_date():
    assert _index_prefix("logs-2025.05.01") == "logs"


def test_prefix_strips_monthly_date():
    assert _index_prefix("audit-2025.05") == "audit"


def test_prefix_strips_multi_segment_name():
    assert _index_prefix("logs-aws-2025.05.01") == "logs-aws"


def test_prefix_unchanged_when_no_date():
    assert _index_prefix("myindex") == "myindex"


def test_prefix_unchanged_for_hidden_index():
    assert _index_prefix(".kibana") == ".kibana"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    with patch("src.capabilities.subagents.data.elastic_data_agent.ElasticsearchEngine") as mock_engine_cls:
        mock_engine = AsyncMock()
        mock_engine_cls.return_value = mock_engine
        a = ElasticDataAgent(
            name="test_es",
            model=TestModel(),
            host="https://es:9200",
            api_key="key",
        )
        a._engine = mock_engine
        yield a, mock_engine


# ---------------------------------------------------------------------------
# initialize()
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_initialize_groups_sharded_indices(agent):
    a, engine = agent
    engine.list_tables = AsyncMock(
        return_value=[
            TableInfo(name="logs-2025.05.01"),
            TableInfo(name="logs-2025.05.02"),
            TableInfo(name="audit-2025.05.01"),
        ]
    )
    engine.get_schema = AsyncMock(return_value=[ColumnInfo(name="@timestamp", type="date", notnull=False, pk=False)])
    engine.get_sample = AsyncMock(return_value=[{"@timestamp": "2025-05-01"}])

    await a.initialize()

    desc = a.routing_description
    assert "logs-* (2 shards)" in desc
    assert "audit-2025.05.01" in desc
    assert "2025.05.02" not in desc  # second shard not listed individually


@pytest.mark.anyio
async def test_initialize_sets_routing_description(agent):
    a, engine = agent
    engine.list_tables = AsyncMock(return_value=[TableInfo(name="myindex")])
    engine.get_schema = AsyncMock(return_value=[ColumnInfo(name="user", type="keyword", notnull=False, pk=False)])
    engine.get_sample = AsyncMock(return_value=[{"user": "alice"}])

    await a.initialize()

    assert "test_es" in a.routing_description
    assert "myindex" in a.routing_description
    assert "user" in a.routing_description


@pytest.mark.anyio
async def test_initialize_no_indices(agent):
    a, engine = agent
    engine.list_tables = AsyncMock(return_value=[])

    await a.initialize()

    assert "no indices found" in a.routing_description


@pytest.mark.anyio
async def test_initialize_raises_on_connection_failure(agent):
    a, engine = agent
    engine.list_tables = AsyncMock(side_effect=Exception("connection refused"))

    with pytest.raises(Exception, match="connection refused"):
        await a.initialize()


@pytest.mark.anyio
async def test_initialize_handles_schema_failure_gracefully(agent):
    a, engine = agent
    engine.list_tables = AsyncMock(return_value=[TableInfo(name="myindex")])
    engine.get_schema = AsyncMock(side_effect=Exception("mapping error"))
    engine.get_sample = AsyncMock(return_value=[])

    await a.initialize()

    assert "schema unavailable" in a.routing_description


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_close_delegates_to_engine(agent):
    a, engine = agent
    engine.close = AsyncMock()
    await a.close()
    engine.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# instructions / constraints
# ---------------------------------------------------------------------------


def test_instructions_contain_esql_guidance(agent):
    a, _ = agent
    assert "ES|QL" in a.instructions or "esql" in a.instructions.lower()
    assert "FROM" in a.instructions
    assert "subqueries" in a.instructions.lower() or "subquery" in a.instructions.lower()


def test_constraints_mention_limit(agent):
    a, _ = agent
    combined = " ".join(a.constraints).lower()
    assert "limit" in combined
