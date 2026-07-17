"""POST /triage/run — run one pass of the triage loop over the configured platform."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.adapters.platforms.loop import run_once

router = APIRouter()


@router.post("/triage/run")
def run_triage(request: Request, limit: int | None = None) -> JSONResponse:
    """Trigger one triage pass: fetch open items, investigate each, write results back.

    `?limit=N` bounds how many alerts this pass triages (omit for all open).
    Scheduling is out of scope — this is the manual/trigger surface.
    """
    handled = run_once(
        request.app.state.orchestrator,
        request.app.state.triage_platform,
        hint="siem",
        limit=limit,
    )
    return JSONResponse({"triaged": len(handled)})
