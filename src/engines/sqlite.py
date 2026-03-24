"""SQLite query engine."""

import re
import sqlite3
import threading

import logfire

from src.engines.base import ColumnInfo, Engine, TableInfo


class SQLiteEngine(Engine):
    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()

    def _safe_table(self, table: str) -> str:
        """Validate table name to prevent injection."""
        if not re.match(r"^[a-zA-Z0-9_]+$", table):
            raise ValueError(f"Invalid table name: {table!r}")
        return table

    @logfire.instrument("list_tables")
    def list_tables(self) -> list[TableInfo]:
        """Return all table names available in the database."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        return [TableInfo(name=row["name"]) for row in rows]

    @logfire.instrument("get_schema")
    def get_schema(self, table: str) -> list[ColumnInfo]:
        """Return column names, types, and constraints for the given table."""
        table = self._safe_table(table)
        with self._lock:
            rows = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [
            ColumnInfo(
                name=row["name"],
                type=row["type"],
                notnull=bool(row["notnull"]),
                pk=bool(row["pk"]),
            )
            for row in rows
        ]

    @logfire.instrument("get_sample")
    def get_sample(self, table: str, n: int = 5) -> list[dict[str, object]]:
        """Return n sample rows from the table to understand its structure and values."""
        table = self._safe_table(table)
        with self._lock:
            rows = self._conn.execute(f"SELECT * FROM {table} LIMIT {n}").fetchall()
        return [dict(row) for row in rows]

    @logfire.instrument("run_query")
    def run_query(self, sql: str) -> list[dict[str, object]]:
        """Execute a read-only SQLite SELECT query and return matching rows.
        Use only columns you need — never SELECT *. Single statement only."""
        sql = sql.split(";")[0].strip()
        if "limit" not in sql.lower():
            sql += " LIMIT 500"
        with self._lock:
            rows = self._conn.execute(sql).fetchall()
        logfire.info("run_query result", row_count=len(rows))
        return [dict(row) for row in rows]

    def init_store(self, table: str) -> None:
        """Create a key-value JSON store table if it does not exist."""
        table = self._safe_table(table)
        with self._lock:
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} "
                "(id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            self._conn.commit()

    def upsert(self, table: str, record_id: str, data: str) -> None:
        """Insert or replace a JSON record by record_id."""
        table = self._safe_table(table)
        with self._lock:
            self._conn.execute(
                f"INSERT OR REPLACE INTO {table} (id, data) VALUES (?, ?)",
                (record_id, data),
            )
            self._conn.commit()

    def fetch(self, table: str, record_id: str) -> str | None:
        """Return the raw JSON string for the given record_id, or None if not found."""
        table = self._safe_table(table)
        with self._lock:
            row = self._conn.execute(
                f"SELECT data FROM {table} WHERE id = ?", (record_id,)
            ).fetchone()
        return row["data"] if row else None

    def fetch_all(self, table: str) -> list[str]:
        """Return raw JSON strings for all records in the table."""
        table = self._safe_table(table)
        with self._lock:
            rows = self._conn.execute(f"SELECT data FROM {table}").fetchall()
        return [row["data"] for row in rows]
