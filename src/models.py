"""Persistence models — generic CRUD base, concrete models, and factory.

BaseModel provides engine-backed CRUD; subclasses declare the schema type and table.
ModelFactory wires the configured engine so callers never touch config directly.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel as PydanticBaseModel

from src.config import config
from src.engines.base import Engine
from src.engines.sqlite import SQLiteEngine
from src.schemas.investigation import Investigation

M = TypeVar("M", bound=PydanticBaseModel)


class BaseModel(Generic[M]):
    """Engine-backed model. Subclasses declare _model_type and _table."""

    _model_type: type[M]
    _table: str

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._engine.init_store(self._table)

    def save(self, item: M) -> None:
        """Insert or replace a record by id."""
        self._engine.upsert(  # type: ignore[attr-defined]
            self._table, item.id, item.model_dump_json()
        )

    def get(self, record_id: str) -> M | None:
        """Return the record with the given id, or None if not found."""
        data = self._engine.fetch(self._table, record_id)
        return self._model_type.model_validate_json(data) if data is not None else None

    def list(self) -> list[M]:
        """Return all records in the table."""
        return [
            self._model_type.model_validate_json(d)
            for d in self._engine.fetch_all(self._table)
        ]


class InvestigationModel(BaseModel[Investigation]):
    """Stores Investigation records."""

    _model_type = Investigation
    _table = "investigations"


class ModelFactory:
    """Creates model instances wired to the configured engine."""

    @staticmethod
    def investigations(db_path: str | None = None) -> InvestigationModel:
        """Return an InvestigationModel backed by the given or configured db_path."""
        return InvestigationModel(SQLiteEngine(db_path or config.persistence.db_path))
