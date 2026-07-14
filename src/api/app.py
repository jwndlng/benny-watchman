"""FastAPI application factory."""

import secrets
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.api.routes.hunt import router as hunt_router
from src.api.routes.investigate import router as investigate_router
from src.api.routes.investigations import router as investigations_router
from src.api.routes.reports import router as reports_router
from src.api.routes.runbooks import router as runbooks_router
from src.capabilities.data.elastic_data_agent import ElasticDataAgent
from src.capabilities.data.sqlite_data_agent import SQLiteDataAgent
from src.capabilities.identity.okta import OktaClient
from src.config import Config, config
from src.core.orchestration.capabilities import Capabilities
from src.core.orchestration.module_registry import ModuleRegistry
from src.core.orchestration.orchestrator import OrchestratorAgent
from src.core.orchestration.runbook_registry import RunbookRegistry
from src.mcp.server.app import MCPServer
from src.models import ModelFactory
from src.modules.siem.module import SIEMModule


def create_app(cfg: Config = config) -> FastAPI:
    """Create and configure the FastAPI application."""

    mcp_token = cfg.mcp_bearer_token or secrets.token_urlsafe(32)
    if not cfg.mcp_bearer_token:
        print(f"MCP bearer token: {mcp_token}", flush=True)

    mcp_server = MCPServer()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Initialise shared state on startup."""
        async with mcp_server.session():
            registry = RunbookRegistry()
            registry.load(cfg.runbooks.path)

            data_agent = SQLiteDataAgent(
                name=cfg.data.name,
                model=cfg.agent.model,
                db_path=cfg.data.db_path,
            )
            await data_agent.initialize()

            elastic_agent = (
                ElasticDataAgent(
                    name="elasticsearch",
                    model=cfg.agent.model,
                    host=cfg.elastic.host,
                    api_key=cfg.elastic.api_key,
                    index_pattern=cfg.elastic.index_pattern,
                )
                if cfg.elastic is not None
                else None
            )
            if elastic_agent is not None:
                await elastic_agent.initialize()

            okta_client = (
                OktaClient(
                    org_url=cfg.okta.domain,
                    client_id=cfg.okta.client_id,
                    private_key_b64=cfg.okta.private_key_b64,
                )
                if cfg.okta is not None
                else None
            )

            data_agents = [data_agent]
            if elastic_agent is not None:
                data_agents.append(elastic_agent)

            mcp_server.register(data_agents, registry)

            persistence = ModelFactory.investigations(db_path=cfg.persistence.db_path)

            capabilities = Capabilities(
                data={agent.name: agent for agent in data_agents},
                identity=okta_client,
            )
            module_registry = ModuleRegistry()
            module_registry.register(
                SIEMModule(model=cfg.agent.model, runbooks=registry)
            )

            app.state.orchestrator = OrchestratorAgent(
                module_registry, persistence, capabilities
            )
            app.state.persistence = persistence
            app.state.registry = registry
            yield

            if elastic_agent is not None:
                await elastic_agent.close()

    app = FastAPI(title="Benny Watchman", lifespan=lifespan)
    app.include_router(investigate_router)
    app.include_router(investigations_router)
    app.include_router(reports_router)
    app.include_router(runbooks_router)
    app.include_router(hunt_router)
    mcp_server.mount(app, mcp_token)

    return app
