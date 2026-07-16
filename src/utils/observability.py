"""Logging + Logfire setup — call once at the process entry point before anything else."""

import logging
import logging.config
import os
import sys

import logfire
import structlog

logger = logging.getLogger(__name__)

_TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"

# Third-party loggers that emit a line per HTTP call. They still flow through the
# unified renderer; we just raise their threshold so per-request chatter (field_caps,
# signals/search, …) doesn't drown out Benny's own logs.
_NOISY_LOGGERS = ("httpx", "httpcore", "elastic_transport", "elasticsearch")


def configure_logging() -> None:
    """Route every log line — uvicorn, FastMCP, httpx, and Benny's own — through one
    structlog renderer: colored console in dev, single-line JSON in prod.

    Uses structlog's ProcessorFormatter so plain stdlib loggers (which is what the
    rest of the app uses) render identically to structlog-native ones — no code
    changes needed elsewhere.

    Call this FIRST at the entry point — before create_app (whose FastMCP init calls
    logging.basicConfig) and before uvicorn.run. Because we configure root first,
    their default handlers see root already set up and stay out of the way.

    Env:
      LOG_LEVEL   root level (default INFO).
      LOG_FORMAT  "console" (colored, human-readable, default) or "json".
    """
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    fmt = os.environ.get("LOG_FORMAT", "console").lower()

    timestamper = structlog.processors.TimeStamper(fmt=_TIMESTAMP_FMT)
    # Applied to records coming from plain stdlib loggers (uvicorn, mcp, httpx, …).
    foreign_pre_chain = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
    ]

    if fmt == "json":
        render = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        render = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()),
        ]

    # Keep third-party chatter unless the operator explicitly asked for DEBUG.
    noisy_level = level if level == "DEBUG" else "WARNING"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "benny": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": render,
                    "foreign_pre_chain": foreign_pre_chain,
                }
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "formatter": "benny",
                    "stream": "ext://sys.stdout",
                }
            },
            # uvicorn.* have no handlers here → they propagate to root and share our
            # renderer (this depends on uvicorn.run being called with log_config=None).
            "loggers": {name: {"level": noisy_level} for name in _NOISY_LOGGERS},
            "root": {"level": level, "handlers": ["stdout"]},
        }
    )

    # Configure structlog-native loggers to hand off to the same ProcessorFormatter,
    # so structlog.get_logger() output is consistent with the stdlib path above.
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def setup_observability(fastapi_app: object = None) -> None:
    """Configure Logfire instrumentation for PydanticAI and optionally FastAPI.

    No-ops when LOGFIRE_TOKEN is unset — app starts without observability. Logfire's
    own console output is disabled (console=False) so traces flow only to the Logfire
    backend; the local console stays on the unified structlog format (configure_logging).
    """
    if not os.environ.get("LOGFIRE_TOKEN"):
        logger.warning("LOGFIRE_TOKEN not set — running without observability")
        return
    logfire.configure(distributed_tracing=True, console=False)
    logfire.instrument_pydantic_ai()
    if fastapi_app is not None:
        logfire.instrument_fastapi(fastapi_app)
