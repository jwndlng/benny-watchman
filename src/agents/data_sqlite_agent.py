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


class DataSQLiteAgent(DataAgent):
    def __init__(self, model: str, instructions: str, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        super().__init__(
            model=model, instructions=instructions + self._schema_context()
        )

        self.agent.tool_plain(self.list_tables)
        self.agent.tool_plain(self.get_schema)
        self.agent.tool_plain(self.get_sample)
        self.agent.tool_plain(self.run_query)

    def _safe_table(self, table: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", table):
            raise ValueError(f"Invalid table name: {table!r}")
        return table

    def _schema_context(self) -> str:
        tables = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        if not tables:
            return "\n\nNo tables found in the database."
        lines = ["\n\nAvailable schema:"]
        for table_row in tables:
            table = table_row["name"]
            lines.append(f"\nTable: {table}")
            cols = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
            for col in cols:
                flags = " ".join(
                    filter(
                        None,
                        [
                            "NOT NULL" if col["notnull"] else "",
                            "PK" if col["pk"] else "",
                        ],
                    )
                )
                lines.append(f"  - {col['name']} ({col['type']}) {flags}".rstrip())
        return "\n".join(lines)

    def list_tables(self) -> list[TableInfo]:
        rows = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [TableInfo(name=row["name"]) for row in rows]

    def get_schema(self, table: str) -> list[ColumnInfo]:
        table = self._safe_table(table)
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

    def get_sample(self, table: str, n: int = 5) -> list[dict]:
        table = self._safe_table(table)
        rows = self._conn.execute(f"SELECT * FROM {table} LIMIT {n}").fetchall()
        return [dict(row) for row in rows]

    def run_query(self, sql: str) -> list[dict]:
        if "limit" not in sql.lower():
            sql = sql.rstrip("; ") + " LIMIT 500"
        rows = self._conn.execute(sql).fetchall()
        return [dict(row) for row in rows]
