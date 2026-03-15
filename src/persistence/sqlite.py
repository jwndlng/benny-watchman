"""SQLite persistence backend — default for local development."""

import sqlite3
from src.persistence.base import PersistenceBackend
from src.schemas.investigation import Investigation


class SQLitePersistence(PersistenceBackend):

    def __init__(self, db_path: str = "investigations.db") -> None:
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS investigations "
                "(id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )

    def save(self, investigation: Investigation) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO investigations (id, data) VALUES (?, ?)",
                (investigation.id, investigation.model_dump_json()),
            )

    def get(self, investigation_id: str) -> Investigation | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM investigations WHERE id = ?", (investigation_id,)
            ).fetchone()
        if row is None:
            return None
        return Investigation.model_validate_json(row["data"])

    def list(self) -> list[Investigation]:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM investigations").fetchall()
        return [Investigation.model_validate_json(row["data"]) for row in rows]
