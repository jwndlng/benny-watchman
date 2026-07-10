"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.agents.data.elastic_data_agent import ElasticDataAgent
from src.agents.data.sqlite_data_agent import SQLiteDataAgent
from src.api.routes.hunt import router as hunt_router
from src.api.routes.investigate import router as investigate_router
from src.api.routes.investigations import router as investigations_router
from src.api.routes.reports import router as reports_router
from src.api.routes.runbooks import router as runbooks_router
from src.config import Config, config
from src.integrations.okta import OktaClient
from src.models import ModelFactory
from src.orchestrator import Orchestrator
from src.runbook_registry import RunbookRegistry


def create_app(cfg: Config = config) -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Initialise shared state on startup."""
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

        persistence = ModelFactory.investigations(db_path=cfg.persistence.db_path)
        app.state.orchestrator = Orchestrator(
            registry,
            persistence,
            model=cfg.agent.model,
            data_agents=data_agents,
            okta_client=okta_client,
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
    return app
