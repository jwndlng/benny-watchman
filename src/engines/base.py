"""Engine ABC — common interface for all query backends."""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class TableInfo(BaseModel):
    name: str


class ColumnInfo(BaseModel):
    name: str
    type: str
    notnull: bool
    pk: bool


class Engine(ABC):
    @abstractmethod
    def list_tables(self) -> list[TableInfo]:
        """Return all table names available in the backend."""
        ...

    @abstractmethod
    def get_schema(self, table: str) -> list[ColumnInfo]:
        """Return column names, types, and constraints for the given table."""
        ...

    @abstractmethod
    def get_sample(self, table: str, n: int = 5) -> list[dict[str, object]]:
        """Return n sample rows from the table to understand its structure and values."""
        ...

    @abstractmethod
    def run_query(self, sql: str) -> list[dict[str, object]]:
        """Execute a read-only query and return matching rows.
        Use only columns you need — never SELECT *. Single statement only."""
        ...

    # --- JSON key-value store (used by DatabaseModel for persistence) ---

    @abstractmethod
    def init_store(self, table: str) -> None:
        """Create a key-value JSON store table if it does not exist."""
        ...

    @abstractmethod
    def upsert(self, table: str, id: str, data: str) -> None:
        """Insert or replace a JSON record by id."""
        ...

    @abstractmethod
    def fetch(self, table: str, id: str) -> str | None:
        """Return the raw JSON string for the given id, or None if not found."""
        ...

    @abstractmethod
    def fetch_all(self, table: str) -> list[str]:
        """Return raw JSON strings for all records in the table."""
        ...

    # --- Schema introspection helpers ---

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
