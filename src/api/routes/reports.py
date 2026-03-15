"""GET /reports — list reports and retrieve by investigation id."""

from flask import Blueprint, jsonify, current_app

bp = Blueprint("reports", __name__)


@bp.get("/reports")
def list_reports():
    investigations = current_app.persistence.list()
    reports = [
        i.report.model_dump(mode="json") for i in investigations if i.report is not None
    ]
    return jsonify(reports), 200


@bp.get("/reports/<investigation_id>")
def get_report(investigation_id: str):
    investigation = current_app.persistence.get(investigation_id)
    if investigation is None or investigation.report is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(investigation.report.model_dump(mode="json")), 200
