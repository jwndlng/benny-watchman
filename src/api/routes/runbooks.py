"""GET /runbooks — list available Runbooks."""

from flask import Blueprint, jsonify

bp = Blueprint("runbooks", __name__)


@bp.get("/runbooks")
def list_runbooks():
    # Stub response — RunbookRegistry not yet implemented
    return jsonify([]), 200
