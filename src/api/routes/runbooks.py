"""GET /runbooks — list runbooks and retrieve by name."""

from flask import Blueprint, jsonify, current_app

bp = Blueprint("runbooks", __name__)


@bp.get("/runbooks")
def list_runbooks():
    runbooks = current_app.registry.list()
    return jsonify([{"name": r.name, "description": r.description} for r in runbooks]), 200


@bp.get("/runbooks/<runbook_name>")
def get_runbook(runbook_name: str):
    runbook = current_app.registry.get(runbook_name)
    if runbook is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(runbook.model_dump()), 200
