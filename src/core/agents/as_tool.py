"""Expose a sub-agent as a PydanticAI tool — the generic sub-agent→tool bridge.

Lets a parent agent call a child sub-agent as one named tool without hand-writing
the delegation boilerplate. A framework concern (depends only on BaseAgent), so it
lives in core; domain-specific naming/description is supplied by the caller.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import logfire

from src.core.agents.base_agent import BaseAgent


def agent_as_tool[T](
    agent: BaseAgent[T],
    *,
    name: str,
    description: str,
) -> Callable[[str], Awaitable[T]]:
    """Wrap ``agent.run(request)`` as a named async tool returning its output.

    ``name`` becomes the PydanticAI tool name (and the span name); ``description``
    becomes the tool docstring the parent LLM sees. Dynamic tool names can't be
    fixed methods, so this factory is the deliberate exception to the no-closures rule.
    """

    # No return annotation on the closure: PydanticAI introspects it to build the
    # tool, and a leaked type-param (T) is an unresolvable ForwardRef at that point.
    async def tool_fn(request: str):  # noqa: ANN202
        with logfire.span(name, request=request):
            result = await agent.run(request)
            return result.output

    tool_fn.__name__ = name
    tool_fn.__doc__ = description
    return tool_fn
