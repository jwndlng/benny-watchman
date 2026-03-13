"""GET /investigations/{id} — retrieve a past investigation."""

from flask import Blueprint, jsonify

bp = Blueprint("investigations", __name__)


@bp.get("/investigations/<investigation_id>")
def get_investigation(investigation_id: str):
    # Stub response — persistence not yet implemented
    return jsonify({"error": "Not implemented"}), 501
