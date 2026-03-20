"""Flask application factory."""

from flask import Flask

from src.api.routes.hunt import bp as hunt_bp
from src.api.routes.investigate import bp as investigate_bp
from src.api.routes.investigations import bp as investigations_bp
from src.api.routes.reports import bp as reports_bp
from src.api.routes.runbooks import bp as runbooks_bp
from src.config import config
from src.models import ModelFactory
from src.orchestrator import Orchestrator
from src.runbook_registry import RunbookRegistry


def create_app(cfg=config) -> Flask:
    app = Flask(__name__)

    registry = RunbookRegistry()
    registry.load(cfg.runbooks.path)

    persistence = ModelFactory.investigations(db_path=cfg.persistence.db_path)
    app.orchestrator = Orchestrator(registry, persistence, model=cfg.agent.model)
    app.persistence = persistence
    app.registry = registry

    app.register_blueprint(investigate_bp)
    app.register_blueprint(investigations_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(runbooks_bp)
    app.register_blueprint(hunt_bp)
    return app
