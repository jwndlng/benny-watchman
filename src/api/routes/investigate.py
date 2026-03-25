"""POST /investigate — submit an alert, returns an Investigation."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.schemas.investigate_request import InvestigateRequest
from src.schemas.alert import Alert

router = APIRouter()


@router.post("/investigate", status_code=202)
def investigate(body: InvestigateRequest, request: Request) -> JSONResponse:
    """Submit an alert for investigation and return the resulting Investigation."""
    alert = Alert(**body.model_dump())
    investigation = request.app.state.orchestrator.investigate(alert)
    if investigation is None:
        return JSONResponse(
            {"error": "No matching runbook found. Manual review required."},
            status_code=422,
        )
    return JSONResponse(investigation.model_dump(mode="json"), status_code=202)
