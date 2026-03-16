"""SQLite-backed DataAgent — owns the connection and registers query tools.

Schema is pre-loaded into the system prompt at init time so the agent
knows what data is available without spending tool calls on discovery.
Tools remain available for fresh queries during the investigation.
"""

import re
import sqlite3

from pydantic import BaseModel

from src.agents.data_agent import DataAgent


class TableInfo(BaseModel):
    name: str


class ColumnInfo(BaseModel):
    name: str
    type: str
    notnull: bool
    pk: bool


def _build_schema_context(conn: sqlite3.Connection) -> str:
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    if not tables:
        return "\n\nNo tables found in the database."
    lines = ["\n\nAvailable schema:"]
    for table_row in tables:
        table = table_row["name"]
        lines.append(f"\nTable: {table}")
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        for col in cols:
            flags = " ".join(
                filter(
                    None,
                    ["NOT NULL" if col["notnull"] else "", "PK" if col["pk"] else ""],
                )
            )
            lines.append(f"  - {col['name']} ({col['type']}) {flags}".rstrip())
    return "\n".join(lines)


def _safe_table(table: str) -> str:
    if not re.match(r"^[a-zA-Z0-9_]+$", table):
        raise ValueError(f"Invalid table name: {table!r}")
    return table


class DataSQLiteAgent(DataAgent):
    def __init__(self, model: str, instructions: str, db_path: str) -> None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        schema_context = _build_schema_context(conn)
        super().__init__(model=model, instructions=instructions + schema_context)

        @self.agent.tool_plain
        def list_tables() -> list[TableInfo]:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            return [TableInfo(name=row["name"]) for row in rows]

        @self.agent.tool_plain
        def get_schema(table: str) -> list[ColumnInfo]:
            table = _safe_table(table)
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return [
                ColumnInfo(
                    name=row["name"],
                    type=row["type"],
                    notnull=bool(row["notnull"]),
                    pk=bool(row["pk"]),
                )
                for row in rows
            ]

        @self.agent.tool_plain
        def get_sample(table: str, n: int = 5) -> list[dict]:
            table = _safe_table(table)
            rows = conn.execute(f"SELECT * FROM {table} LIMIT {n}").fetchall()
            return [dict(row) for row in rows]

        @self.agent.tool_plain
        def run_query(sql: str) -> list[dict]:
            if "limit" not in sql.lower():
                sql = sql.rstrip("; ") + " LIMIT 500"
            rows = conn.execute(sql).fetchall()
            return [dict(row) for row in rows]
