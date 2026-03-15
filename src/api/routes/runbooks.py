"""GET /runbooks — list runbooks and retrieve by id."""

from flask import Blueprint, jsonify

bp = Blueprint("runbooks", __name__)


@bp.get("/runbooks")
def list_runbooks():
    # Stub — RunbookRegistry not yet implemented
    return jsonify([]), 200


@bp.get("/runbooks/<runbook_id>")
def get_runbook(runbook_id: str):
    # Stub — RunbookRegistry not yet implemented
    return jsonify({"error": "Not found"}), 404
