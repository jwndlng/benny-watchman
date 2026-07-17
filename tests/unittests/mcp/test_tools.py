"""MCP tool surface: list_modules replaces list_runbooks."""

import json
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from src.mcp.server.tools import register_tools


def _mcp() -> FastMCP:
    mcp = FastMCP("test")
    siem = MagicMock()
    siem.name = "siem"
    siem.input_type = type("Alert", (), {})
    vuln = MagicMock()
    vuln.name = "vuln_mgmt"
    vuln.input_type = type("Finding", (), {})
    registry = MagicMock()
    registry.list.return_value = [siem, vuln]
    register_tools(
        mcp,
        data_agents=[],
        module_registry=registry,
        orchestrator=MagicMock(),
        platform=MagicMock(),
    )
    return mcp


@pytest.mark.anyio
async def test_list_modules_replaces_list_runbooks():
    tools = await _mcp().list_tools()
    names = {t.name for t in tools}
    assert "list_modules" in names
    assert "list_runbooks" not in names


@pytest.mark.anyio
async def test_list_modules_returns_module_names_and_input_types():
    content, _ = await _mcp().call_tool("list_modules", {})
    payload = json.loads(content[0].text)
    assert {m["name"] for m in payload} == {"siem", "vuln_mgmt"}
    assert {m["input_type"] for m in payload} == {"Alert", "Finding"}
