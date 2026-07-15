"""POST /triage/run — run one pass of the triage loop over the configured platform."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.platforms.loop import run_once

router = APIRouter()


@router.post("/triage/run")
def run_triage(request: Request) -> JSONResponse:
    """Trigger one triage pass: fetch open items, investigate each, write results back.

    Scheduling is out of scope — this is the manual/trigger surface. In dev the
    configured platform is in-memory; a real platform (e.g. Elastic) is a follow-up.
    """
    handled = run_once(
        request.app.state.orchestrator,
        request.app.state.triage_platform,
        hint="siem",
    )
    return JSONResponse({"triaged": len(handled)})
