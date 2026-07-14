"""POST /investigate — submit an alert, returns an Investigation."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.schemas.investigate_request import InvestigateRequest

router = APIRouter()


@router.post("/investigate", status_code=202)
def investigate(body: InvestigateRequest, request: Request) -> JSONResponse:
    """Submit an alert for investigation and return the resulting Investigation."""
    investigation = request.app.state.orchestrator.handle(
        body.model_dump(), hint="siem"
    )
    if investigation is None:
        return JSONResponse(
            {"error": "No module could handle this alert. Manual review required."},
            status_code=422,
        )
    return JSONResponse(investigation.model_dump(mode="json"), status_code=202)
