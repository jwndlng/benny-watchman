"""GET /investigations — list investigations and retrieve by id."""

from flask import Blueprint, jsonify, current_app

bp = Blueprint("investigations", __name__)


@bp.get("/investigations")
def list_investigations():
    investigations = current_app.persistence.list()
    return jsonify([i.model_dump(mode="json") for i in investigations]), 200


@bp.get("/investigations/<investigation_id>")
def get_investigation(investigation_id: str):
    investigation = current_app.persistence.get(investigation_id)
    if investigation is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(investigation.model_dump(mode="json")), 200
