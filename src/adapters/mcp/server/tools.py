"""MCP tool registration for the Benny Streamable HTTP server."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

import anyio

from mcp.server.fastmcp import FastMCP

from src.capabilities.subagents.data.base_data_agent import BaseDataAgent
from src.adapters.platforms.loop import run_once

if TYPE_CHECKING:
    from src.core.orchestration.module_registry import ModuleRegistry
    from src.core.orchestration.orchestrator import OrchestratorAgent
    from src.adapters.platforms.base import TriagePlatform


def register_tools(
    mcp: FastMCP,
    data_agents: list[BaseDataAgent],
    module_registry: ModuleRegistry,
    orchestrator: OrchestratorAgent,
    platform: TriagePlatform,
) -> None:
    """Register all MCP tools on the given FastMCP instance.

    Called during FastAPI lifespan after agents are initialised, so tools close
    over live references and share the same components as the REST API.
    """

    @mcp.tool()
    async def list_modules() -> str:
        """List the analyst modules Benny can investigate with.

        Returns a JSON array of objects with 'name' and 'input_type' fields.
        Use this to discover what Benny can investigate.
        """
        return json.dumps([{"name": m.name, "input_type": m.input_type.__name__} for m in module_registry.list()])

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
            except Exception as exc:
                return {"source": agent.name, "error": str(exc)}

        results = await asyncio.gather(*[_run_agent(a) for a in data_agents])
        return json.dumps(list(results))

    @mcp.tool()
    async def check_platform_access() -> str:
        """Check the triage platform's connectivity and privileges WITHOUT triaging.

        Read-only: verifies Benny can reach the SIEM (Kibana), read alerts, and
        access cases, and reports how many open alerts are waiting. Use this to
        validate KIBANA_URL / KIBANA_TRIAGE_API_KEY and the key's privileges before
        running a triage — it makes no changes and runs no investigation.
        """
        status = await anyio.to_thread.run_sync(platform.health_check)
        return json.dumps(status)

    @mcp.tool()
    async def review_newest_alert() -> str:
        """Triage the newest open alert on demand.

        Benny investigates the single most-recent open alert and writes the verdict
        back to the SIEM: opens a case, comments its reasoning, sets the severity,
        and closes it if benign or escalates it if a real threat. Returns the result.
        Use this to have Benny review one alert now, rather than the whole queue.
        """
        # run_once drives the synchronous analyst loop; run it off the event loop.
        handled = await anyio.to_thread.run_sync(lambda: run_once(orchestrator, platform, "siem", 1))
        if not handled:
            return json.dumps({"triaged": 0, "message": "No open alerts to triage."})
        inv = handled[0]
        return json.dumps(
            {
                "triaged": 1,
                "alert_id": inv.alert_id,
                "guidance_source": inv.guidance_source,
                "disposition": inv.outcome.disposition if inv.outcome else None,
                "priority": inv.outcome.priority if inv.outcome else None,
                "summary": (inv.report or {}).get("summary", ""),
            }
        )
