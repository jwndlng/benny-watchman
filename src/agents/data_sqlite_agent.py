"""SQLite-backed DataAgent — owns the connection and registers query tools.

Schema is pre-loaded into the system prompt at init time so the agent
knows what data is available without spending tool calls on discovery.
Tools remain available for fresh queries during the investigation.
"""

import re
import sqlite3
import threading

import logfire
from pydantic import BaseModel

from src.agents.data_agent import DataAgent


class TableInfo(BaseModel):
    name: str


class ColumnInfo(BaseModel):
    name: str
    type: str
    notnull: bool
    pk: bool


class DataSQLiteAgent(DataAgent):
    @property
    def instructions(self) -> str:
        return super().instructions + self._schema_context()

    def __init__(self, model: str, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        super().__init__(model=model)

    def _safe_table(self, table: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", table):
            raise ValueError(f"Invalid table name: {table!r}")
        return table

    def _schema_context(self) -> str:
        tables = self.list_tables()
        if not tables:
            return "\n\nNo tables found in the database."
        lines = ["\n\nAvailable schema:"]
        for table in tables:
            lines.append(f"\nTable: {table.name}")
            for col in self.get_schema(table.name):
                flags = " ".join(
                    filter(None, ["NOT NULL" if col.notnull else "", "PK" if col.pk else ""])
                )
                lines.append(f"  - {col.name} ({col.type}) {flags}".rstrip())
        return "\n".join(lines)

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
        # Take only the first statement — some models generate multi-statement SQL
        sql = sql.split(";")[0].strip()
        if "limit" not in sql.lower():
            sql += " LIMIT 500"
        with self._lock:
            rows = self._conn.execute(sql).fetchall()
        logfire.info("run_query result", row_count=len(rows))
        return [dict(row) for row in rows]
