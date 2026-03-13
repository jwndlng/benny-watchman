"""POST /investigate — submit an alert and receive an Incident Report."""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from src.schemas.alert import Alert
from src.schemas.incident_report import IncidentReport, Severity, Verdict

bp = Blueprint("investigate", __name__)


@bp.post("/investigate")
def investigate():
    try:
        alert = Alert.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    # Stub response — agent logic not yet implemented
    report = IncidentReport(
        alert_id=alert.id,
        severity=Severity.MEDIUM,
        verdict=Verdict.INCONCLUSIVE,
        confidence=0.0,
        summary="Investigation pending — agent not yet implemented.",
        findings=[],
        recommended_actions=[],
        detection_rule_improvements=[],
        runbook="",
    )
    return jsonify(report.model_dump()), 202
