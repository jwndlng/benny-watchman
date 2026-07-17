"""Assembly of Benny's Streamable HTTP MCP server (Benny acting as an MCP server)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from src.mcp.server.auth import BearerAuthMiddleware
from src.mcp.server.tools import register_tools

if TYPE_CHECKING:
    from fastapi import FastAPI

    from src.capabilities.data.base_data_agent import BaseDataAgent
    from src.core.orchestration.module_registry import ModuleRegistry
    from src.core.orchestration.orchestrator import OrchestratorAgent
    from src.platforms.base import TriagePlatform


class MCPServer:
    """Wraps the FastMCP instance and its lifecycle for mounting on FastAPI.

    ``streamable_http_path="/"`` so the sub-app handles "/" after FastAPI strips the
    "/mcp" mount prefix. ``streamable_http_app()`` is built eagerly in ``__init__`` to
    initialise the session manager before FastAPI's own lifespan starts it.
    """

    def __init__(self, name: str = "benny") -> None:
        self._mcp = FastMCP(name, streamable_http_path="/")
        self._asgi_app = self._mcp.streamable_http_app()

    def session(self):
        """Session-manager context to enter inside the FastAPI lifespan."""
        return self._mcp.session_manager.run()

    def register(
        self,
        data_agents: list[BaseDataAgent],
        module_registry: ModuleRegistry,
        orchestrator: OrchestratorAgent,
        platform: TriagePlatform,
    ) -> None:
        """Register Benny's MCP tools once dependencies are initialised."""
        register_tools(self._mcp, data_agents, module_registry, orchestrator, platform)

    def mount(self, app: FastAPI, token: str) -> None:
        """Mount the bearer-authenticated MCP ASGI app at /mcp."""
        app.mount("/mcp", BearerAuthMiddleware(self._asgi_app, token))
