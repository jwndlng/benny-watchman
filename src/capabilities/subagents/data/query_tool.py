"""Factory for the per-DataAgent query tool used by analyst agents.

Shared across analyst modules (SIEM, VM, …) so each can expose one query tool
per data source without duplicating the delegation boilerplate. A thin,
data-specific wrapper over core's generic ``agent_as_tool`` bridge.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from src.core.agents.as_tool import agent_as_tool
from src.capabilities.subagents.data.base_data_agent import BaseDataAgent, DataModel


def make_query_tool(data_agent: BaseDataAgent) -> Callable[[str], Awaitable[DataModel]]:
    """Create a named async tool (``query_{agent.name}``) delegating to the DataAgent.

    The function name becomes the PydanticAI tool name and the agent's
    ``routing_description`` becomes the tool description seen by the LLM.
    """
    return agent_as_tool(
        data_agent,
        name=f"query_{data_agent.name}",
        description=data_agent.routing_description,
    )
