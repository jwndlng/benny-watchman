"""Logfire observability setup — call once at each entry point before anything else."""

import logfire


def setup_observability(flask_app=None) -> None:
    """Configure Logfire instrumentation for PydanticAI and optionally Flask."""
    logfire.configure(distributed_tracing=True)
    logfire.instrument_pydantic_ai()
    if flask_app is not None:
        logfire.instrument_flask(flask_app)
