"""MCP tool registration for the Benny Streamable HTTP server."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from src.agents.data.base_data_agent import BaseDataAgent

if TYPE_CHECKING:
    from src.runbook_registry import RunbookRegistry


def register_tools(
    mcp: FastMCP,
    data_agents: list[BaseDataAgent],
    registry: RunbookRegistry,
) -> None:
    """Register all MCP tools on the given FastMCP instance.

    Called during FastAPI lifespan after agents are initialised, so tools
    close over live references and share the same data agents as the REST API.
    """

    @mcp.tool()
    async def list_runbooks() -> str:
        """List all available runbook names and descriptions.

        Returns a JSON array of objects with 'name' and 'description' fields.
        Use this to discover what alert types Benny can investigate.
        """
        return json.dumps(
            [{"name": rb.name, "description": rb.description} for rb in registry.list()]
        )

    @mcp.tool()
    async def lookup_data(query: str) -> str:
        """Look up data from the configured log source(s) using a natural-language query.

        The query is passed to each data agent, which uses its own reasoning loop to
        determine what to query and returns matching rows with context notes.
        Results from all sources are combined. This call may take several seconds.

        Examples:
          "how many failed logins in the last hour?"
          "show me the 5 most recent events for user alice"
          "count authentication events by source IP in the last 24 hours"
        """
        async def _run_agent(agent: BaseDataAgent) -> dict:
            try:
                result = await agent.run(query)
                return {
                    "source": agent.name,
                    "rows": result.output.rows,
                    "notes": result.output.notes,
                }
            except Exception as exc:  # noqa: BLE001
                return {"source": agent.name, "error": str(exc)}

        results = await asyncio.gather(*[_run_agent(a) for a in data_agents])
        return json.dumps(list(results))
