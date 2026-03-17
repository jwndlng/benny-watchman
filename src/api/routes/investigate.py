"""POST /investigate — submit an alert, returns an Investigation."""

from flask import Blueprint, Response, request, jsonify, current_app
from pydantic import ValidationError
from src.api.schemas.investigate_request import InvestigateRequest
from src.schemas.alert import Alert

bp = Blueprint("investigate", __name__)


@bp.post("/investigate")
def investigate() -> tuple[Response, int]:
    """Submit an alert for investigation and return the resulting Investigation."""
    try:
        body = InvestigateRequest.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    alert = Alert(**body.model_dump())
    investigation = current_app.orchestrator.investigate(alert)
    if investigation is None:
        return jsonify(
            {"error": "No matching runbook found. Manual review required."}
        ), 422

    return jsonify(investigation.model_dump(mode="json")), 202
