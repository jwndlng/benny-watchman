"""GET /reports — list reports and retrieve by investigation id."""

from flask import Blueprint, jsonify

bp = Blueprint("reports", __name__)


@bp.get("/reports")
def list_reports():
    # Stub — persistence not yet implemented
    return jsonify([]), 200


@bp.get("/reports/<investigation_id>")
def get_report(investigation_id: str):
    # Stub — persistence not yet implemented
    return jsonify({"error": "Not found"}), 404
