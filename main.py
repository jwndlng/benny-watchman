from src.api.app import create_app
from src.utils.observability import setup_observability

app = create_app()
setup_observability(flask_app=app)

if __name__ == "__main__":
    app.run()
