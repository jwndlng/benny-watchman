"""Unit tests for MCP tool registration."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from src.agents.data.base_data_agent import DataModel
from src.mcp_tools import register_tools


def _make_registry(*runbooks: tuple[str, str]) -> MagicMock:
    registry = MagicMock()
    items = []
    for name, desc in runbooks:
        rb = MagicMock()
        rb.name = name
        rb.description = desc
        items.append(rb)
    registry.list.return_value = items
    return registry


def _make_agent(name: str, rows: list, notes: str = "") -> MagicMock:
    agent = MagicMock()
    agent.name = name
    result = MagicMock()
    result.output = DataModel(rows=rows, notes=notes)
    agent.run = AsyncMock(return_value=result)
    return agent


@pytest.fixture
def mcp_instance() -> FastMCP:
    return FastMCP("test")


# --- list_runbooks ---


@pytest.mark.anyio
async def test_list_runbooks_returns_json_array(mcp_instance):
    registry = _make_registry(
        ("brute-force", "Detects brute force"), ("generic", "Fallback")
    )
    register_tools(mcp_instance, [], registry)

    result = await mcp_instance.call_tool("list_runbooks", {})
    data = json.loads(result[0][0].text)
    assert isinstance(data, list)
    assert {"name": "brute-force", "description": "Detects brute force"} in data
    assert {"name": "generic", "description": "Fallback"} in data


@pytest.mark.anyio
async def test_list_runbooks_empty_registry(mcp_instance):
    register_tools(mcp_instance, [], _make_registry())
    result = await mcp_instance.call_tool("list_runbooks", {})
    assert json.loads(result[0][0].text) == []


# --- lookup_data ---


@pytest.mark.anyio
async def test_lookup_data_returns_rows(mcp_instance):
    agent = _make_agent(
        "elastic", [{"user": "alice", "count": 5}], notes="queried last 1h"
    )
    register_tools(mcp_instance, [agent], _make_registry())

    result = await mcp_instance.call_tool("lookup_data", {"query": "failed logins"})
    data = json.loads(result[0][0].text)
    assert len(data) == 1
    assert data[0]["source"] == "elastic"
    assert data[0]["rows"] == [{"user": "alice", "count": 5}]
    assert data[0]["notes"] == "queried last 1h"
    agent.run.assert_awaited_once_with("failed logins")


@pytest.mark.anyio
async def test_lookup_data_multiple_agents(mcp_instance):
    a1 = _make_agent("sqlite", [{"id": 1}])
    a2 = _make_agent("elastic", [{"id": 2}])
    register_tools(mcp_instance, [a1, a2], _make_registry())

    result = await mcp_instance.call_tool("lookup_data", {"query": "test"})
    data = json.loads(result[0][0].text)
    sources = {r["source"] for r in data}
    assert sources == {"sqlite", "elastic"}


@pytest.mark.anyio
async def test_lookup_data_agent_exception_returns_error(mcp_instance):
    agent = MagicMock()
    agent.name = "elastic"
    agent.run = AsyncMock(side_effect=RuntimeError("connection refused"))
    register_tools(mcp_instance, [agent], _make_registry())

    result = await mcp_instance.call_tool("lookup_data", {"query": "test"})
    data = json.loads(result[0][0].text)
    assert data[0]["source"] == "elastic"
    assert "connection refused" in data[0]["error"]
