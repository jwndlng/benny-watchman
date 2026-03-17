"""POST /hunt — trigger an interactive threat hunting session (post-MVP)."""

from flask import Blueprint, Response, jsonify

bp = Blueprint("hunt", __name__)


@bp.post("/hunt")
def hunt() -> tuple[Response, int]:
    """Trigger an interactive threat hunting session (post-MVP)."""
    return jsonify({"error": "Not implemented"}), 501
