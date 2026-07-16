"""POST /hunt — trigger an interactive threat hunting session (post-MVP)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/hunt", status_code=501)
def hunt() -> JSONResponse:
    """Trigger an interactive threat hunting session (post-MVP)."""
    return JSONResponse({"error": "Not implemented"}, status_code=501)
