"""Logfire observability setup — call once at each entry point before anything else."""

import logfire


def setup_observability(fastapi_app: object = None) -> None:
    """Configure Logfire instrumentation for PydanticAI and optionally FastAPI."""
    logfire.configure(distributed_tracing=True)
    logfire.instrument_pydantic_ai()
    if fastapi_app is not None:
        logfire.instrument_fastapi(fastapi_app)
