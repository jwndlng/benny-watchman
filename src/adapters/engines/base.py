"""QueryEngine ABC — query-only interface for all data backends."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class TableInfo(BaseModel):
    """Metadata for a single table in the backend."""

    name: str = Field(description="Table name")


class ColumnInfo(BaseModel):
    """Metadata for a single column in a table."""

    name: str = Field(description="Column name")
    type: str = Field(description="Column type (e.g. TEXT, INTEGER, keyword, date)")
    notnull: bool = Field(description="True if the column has a NOT NULL constraint")
    pk: bool = Field(description="True if the column is part of the primary key")


class QueryEngine(ABC):
    """Query-only interface for data backends (SQLite, Elasticsearch, ClickHouse, etc.).

    Persistence (init_store, upsert, fetch, fetch_all) is not part of this contract
    and lives on SQLiteEngine directly for use by the models layer.
    """

    @abstractmethod
    def list_tables(self) -> list[TableInfo]:
        """Return all table names available in the backend."""

    @abstractmethod
    def get_schema(self, table: str) -> list[ColumnInfo]:
        """Return column names, types, and constraints for the given table."""

    @abstractmethod
    def get_sample(self, table: str, n: int = 5) -> list[dict[str, object]]:
        """Return n sample rows from the table to understand its structure and values."""

    @abstractmethod
    def run_query(self, sql: str) -> list[dict[str, object]]:
        """Execute a read-only query and return matching rows.
        Use only columns you need — never SELECT *. Single statement only."""

    def schema_context(self) -> str:
        """Return a formatted schema summary suitable for injection into a system prompt."""
        tables = self.list_tables()
        if not tables:
            return "\n\nNo tables found in the database."
        lines = ["\n\nAvailable schema:"]
        for table in tables:
            lines.append(f"\nTable: {table.name}")
            for col in self.get_schema(table.name):
                flags = " ".join(
                    filter(
                        None,
                        ["NOT NULL" if col.notnull else "", "PK" if col.pk else ""],
                    )
                )
                lines.append(f"  - {col.name} ({col.type}) {flags}".rstrip())
        return "\n".join(lines)
