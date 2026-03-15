import pytest
from src.api.app import create_app


@pytest.fixture
def client(tmp_path):
    class _Persistence:
        engine = "sqlite"
        db_path = str(tmp_path / "test.db")

    class _Runbooks:
        path = "runbooks"

    class _Config:
        persistence = _Persistence()
        runbooks = _Runbooks()

    app = create_app(cfg=_Config())
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
