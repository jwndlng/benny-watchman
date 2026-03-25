"""GET /reports — list reports and retrieve by investigation id."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/reports")
def list_reports(request: Request) -> JSONResponse:
    """Return all incident reports."""
    investigations = request.app.state.persistence.list()
    reports = [
        i.report.model_dump(mode="json") for i in investigations if i.report is not None
    ]
    return JSONResponse(reports)


@router.get("/reports/{investigation_id}")
def get_report(investigation_id: str, request: Request) -> JSONResponse:
    """Return the incident report for a given investigation ID."""
    investigation = request.app.state.persistence.get(investigation_id)
    if investigation is None or investigation.report is None:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(investigation.report.model_dump(mode="json"))
