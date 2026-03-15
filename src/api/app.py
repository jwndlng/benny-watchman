"""Flask application factory."""

from flask import Flask
from src.api.routes.investigate import bp as investigate_bp
from src.api.routes.investigations import bp as investigations_bp
from src.api.routes.reports import bp as reports_bp
from src.api.routes.runbooks import bp as runbooks_bp
from src.api.routes.hunt import bp as hunt_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(investigate_bp)
    app.register_blueprint(investigations_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(runbooks_bp)
    app.register_blueprint(hunt_bp)
    return app
