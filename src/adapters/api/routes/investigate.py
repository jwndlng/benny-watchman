"""POST /investigate — submit an alert, returns an Investigation."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.schemas.investigate_request import InvestigateRequest

router = APIRouter()


@router.post("/investigate")
def investigate(body: InvestigateRequest, request: Request) -> JSONResponse:
    """Submit an alert for investigation and return the resulting Investigation.

    Idempotent: a repeat submission of the same alert returns the stored
    investigation with 200; a freshly-run investigation returns 202.
    """
    result = request.app.state.orchestrator.handle(body.model_dump(), hint="siem")
    if result.investigation is None:
        return JSONResponse(
            {"error": "No module could handle this alert. Manual review required."},
            status_code=422,
        )
    status_code = 202 if result.created else 200
    return JSONResponse(
        result.investigation.model_dump(mode="json"), status_code=status_code
    )
