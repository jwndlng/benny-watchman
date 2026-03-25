"""GET /runbooks — list runbooks and retrieve by name."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/runbooks")
def list_runbooks(request: Request) -> JSONResponse:
    """Return all loaded runbooks."""
    runbooks = request.app.state.registry.list()
    return JSONResponse(
        [{"name": r.name, "description": r.description} for r in runbooks]
    )


@router.get("/runbooks/{runbook_name}")
def get_runbook(runbook_name: str, request: Request) -> JSONResponse:
    """Return a single runbook by name."""
    runbook = request.app.state.registry.get(runbook_name)
    if runbook is None:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(runbook.model_dump())
