"""Logfire observability setup — call once at each entry point before anything else."""

import logging
import os

import logfire

logger = logging.getLogger(__name__)


def setup_observability(fastapi_app: object = None) -> None:
    """Configure Logfire instrumentation for PydanticAI and optionally FastAPI.

    No-ops when LOGFIRE_TOKEN is unset — app starts without observability.
    """
    if not os.environ.get("LOGFIRE_TOKEN"):
        logger.warning("LOGFIRE_TOKEN not set — running without observability")
        return
    logfire.configure(distributed_tracing=True)
    logfire.instrument_pydantic_ai()
    if fastapi_app is not None:
        logfire.instrument_fastapi(fastapi_app)
