"""POST /findings — submit a vulnerability finding, returns an Investigation."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.modules.vuln_mgmt.finding import Finding

router = APIRouter()


@router.post("/findings")
def triage_finding(body: Finding, request: Request) -> JSONResponse:
    """Submit a vulnerability finding for triage and return the Investigation.

    Idempotent: a repeat submission of the same finding (cve/asset/cvss) returns
    the stored investigation with 200; a freshly-run triage returns 202.
    """
    result = request.app.state.orchestrator.handle(body.model_dump(), hint="vuln_mgmt")
    if result.investigation is None:
        return JSONResponse(
            {"error": "No module could handle this finding. Manual review required."},
            status_code=422,
        )
    status_code = 202 if result.created else 200
    return JSONResponse(
        result.investigation.model_dump(mode="json"), status_code=status_code
    )
