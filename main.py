import uvicorn

from src.api.app import create_app
from src.utils.observability import setup_observability

app = create_app()
setup_observability(fastapi_app=app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
