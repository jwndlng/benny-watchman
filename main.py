import uvicorn

from src.adapters.api.app import create_app
from src.utils.observability import configure_logging, setup_observability

# Configure logging before create_app (FastMCP calls logging.basicConfig on init)
# so every subsystem shares one format.
configure_logging()
app = create_app()
setup_observability(fastapi_app=app)

if __name__ == "__main__":
    # log_config=None: don't let uvicorn install its own handlers — its loggers
    # propagate to the root logger configured above and share the unified format.
    uvicorn.run(app, host="0.0.0.0", port=5000, log_config=None)
