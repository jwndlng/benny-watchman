"""Factory for the per-DataAgent query tool used by analyst agents.

Shared across analyst modules (SIEM, VM, …) so each can expose one query tool
per data source without duplicating the delegation boilerplate.
"""

from __future__ import annotations

from collections.abc import Callable

import logfire
from pydantic_ai import AgentRunResult

from src.capabilities.subagents.data.base_data_agent import BaseDataAgent, DataModel


def make_query_tool(data_agent: BaseDataAgent) -> Callable:
    """Create a named async tool that delegates to the given DataAgent.

    The function name becomes the PydanticAI tool name (``query_{agent.name}``)
    and the docstring becomes the tool description seen by the LLM. Dynamic tool
    names cannot be fixed methods, so this factory is the deliberate exception to
    the no-closures rule.
    """

    async def query_fn(request: str) -> DataModel:
        with logfire.span(f"query_{data_agent.name}", request=request):
            result: AgentRunResult[DataModel] = await data_agent.run(request)
            return result.output

    query_fn.__name__ = f"query_{data_agent.name}"
    query_fn.__doc__ = data_agent.routing_description
    return query_fn
