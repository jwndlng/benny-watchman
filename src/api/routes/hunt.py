"""POST /hunt — trigger an interactive threat hunting session (post-MVP)."""

from flask import Blueprint, jsonify

bp = Blueprint("hunt", __name__)


@bp.post("/hunt")
def hunt():
    return jsonify({"error": "Not implemented"}), 501
