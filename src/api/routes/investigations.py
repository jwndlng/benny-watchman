"""GET /investigations — list investigations and retrieve by id."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/investigations")
def list_investigations(request: Request) -> JSONResponse:
    """Return all investigations."""
    investigations = request.app.state.persistence.list()
    return JSONResponse([i.model_dump(mode="json") for i in investigations])


@router.get("/investigations/{investigation_id}")
def get_investigation(investigation_id: str, request: Request) -> JSONResponse:
    """Return a single investigation by ID."""
    investigation = request.app.state.persistence.get(investigation_id)
    if investigation is None:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(investigation.model_dump(mode="json"))
