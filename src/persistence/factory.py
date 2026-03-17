"""Creates the configured persistence backend from engine name."""

from src.persistence.base import PersistenceBackend


def create_persistence(engine: str, **kwargs) -> PersistenceBackend:
    if engine == "sqlite":
        from src.persistence.sqlite import SQLitePersistence

        return SQLitePersistence(**kwargs)
    if engine == "clickhouse":
        from src.persistence.clickhouse import (
            ClickhousePersistence,
        )  # not yet implemented

        return ClickhousePersistence(**kwargs)
    raise ValueError(f"Unknown persistence engine: {engine!r}")
