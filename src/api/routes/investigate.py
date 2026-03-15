"""POST /investigate — submit an alert, returns an Investigation."""

import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from src.schemas.alert import Alert
from src.schemas.investigation import Investigation, InvestigationStatus

bp = Blueprint("investigate", __name__)


@bp.post("/investigate")
def investigate():
    try:
        alert = Alert.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    # Stub — agent logic not yet implemented
    investigation = Investigation(
        id=str(uuid.uuid4()),
        alert_id=alert.id,
        status=InvestigationStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    return jsonify(investigation.model_dump(mode="json")), 202
