"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.api.routes.hunt import router as hunt_router
from src.api.routes.investigate import router as investigate_router
from src.api.routes.investigations import router as investigations_router
from src.api.routes.reports import router as reports_router
from src.api.routes.runbooks import router as runbooks_router
from src.config import Config, config
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

        persistence = ModelFactory.investigations(db_path=cfg.persistence.db_path)
        app.state.orchestrator = Orchestrator(
            registry, persistence, model=cfg.agent.model
        )
        app.state.persistence = persistence
        app.state.registry = registry
        yield

    app = FastAPI(title="Benny Watchman", lifespan=lifespan)
    app.include_router(investigate_router)
    app.include_router(investigations_router)
    app.include_router(reports_router)
    app.include_router(runbooks_router)
    app.include_router(hunt_router)
    return app
