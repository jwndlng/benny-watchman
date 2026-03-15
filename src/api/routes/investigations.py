"""GET /investigations — list investigations and retrieve by id."""

from flask import Blueprint, jsonify

bp = Blueprint("investigations", __name__)


@bp.get("/investigations")
def list_investigations():
    # Stub — persistence not yet implemented
    return jsonify([]), 200


@bp.get("/investigations/<investigation_id>")
def get_investigation(investigation_id: str):
    # Stub — persistence not yet implemented
    return jsonify({"error": "Not found"}), 404
