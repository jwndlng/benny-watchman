"""Application configuration loaded from environment variables."""

import os


class _PersistenceConfig:
    engine = os.environ.get("PERSISTENCE_ENGINE", "sqlite")
    db_path = os.environ.get("PERSISTENCE_DB_PATH", "investigations.db")


class _RunbooksConfig:
    path = os.environ.get("RUNBOOKS_PATH", "runbooks")


class Config:
    persistence = _PersistenceConfig()
    runbooks = _RunbooksConfig()


config = Config()
