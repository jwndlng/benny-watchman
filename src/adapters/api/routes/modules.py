"""GET /modules — discover the analyst modules Benny can investigate with."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/modules")
def list_modules(request: Request) -> JSONResponse:
    """Return the registered analyst modules and the input types they accept."""
    modules = request.app.state.module_registry.list()
    return JSONResponse(
        [{"name": m.name, "input_type": m.input_type.__name__} for m in modules]
    )
