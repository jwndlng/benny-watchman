"""Unit tests for models.py — BaseModel CRUD and InvestigationModel."""

from datetime import datetime, timezone

import pytest

from src.engines.sqlite import SQLiteEngine
from src.models import InvestigationModel
from src.schemas.incident_report import Severity, Verdict
from src.schemas.investigation import Investigation, InvestigationStatus


def make_investigation(id: str = "inv-001") -> Investigation:
    """Minimal valid Investigation."""
    return Investigation(
        id=id,
        alert_id="alert-001",
        status=InvestigationStatus.COMPLETE,
        severity=Severity.HIGH,
        verdict=Verdict.TRUE_POSITIVE,
        created_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def model(tmp_path):
    """InvestigationModel backed by a fresh in-memory SQLite db."""
    engine = SQLiteEngine(str(tmp_path / "inv.db"))
    return InvestigationModel(engine)


# --- save / get ---

def test_save_and_get_roundtrip(model):
    inv = make_investigation()
    model.save(inv)
    result = model.get("inv-001")
    assert result is not None
    assert result.id == "inv-001"
    assert result.alert_id == "alert-001"
    assert result.status == InvestigationStatus.COMPLETE


def test_get_missing_returns_none(model):
    assert model.get("does-not-exist") is None


def test_save_overwrites_existing(model):
    inv = make_investigation()
    model.save(inv)
    updated = inv.model_copy(update={"status": InvestigationStatus.FAILED})
    model.save(updated)
    result = model.get("inv-001")
    assert result.status == InvestigationStatus.FAILED


# --- list ---

def test_list_empty(model):
    assert model.list() == []


def test_list_returns_all(model):
    model.save(make_investigation("inv-001"))
    model.save(make_investigation("inv-002"))
    ids = {i.id for i in model.list()}
    assert ids == {"inv-001", "inv-002"}


def test_list_preserves_data(model):
    inv = make_investigation()
    model.save(inv)
    results = model.list()
    assert results[0].severity == Severity.HIGH
    assert results[0].verdict == Verdict.TRUE_POSITIVE


# --- isolation ---

def test_separate_instances_share_data(tmp_path):
    """Two models backed by the same db_path see the same data."""
    path = str(tmp_path / "shared.db")
    m1 = InvestigationModel(SQLiteEngine(path))
    m2 = InvestigationModel(SQLiteEngine(path))
    m1.save(make_investigation("inv-shared"))
    assert m2.get("inv-shared") is not None


def test_separate_dbs_are_isolated(tmp_path):
    m1 = InvestigationModel(SQLiteEngine(str(tmp_path / "a.db")))
    m2 = InvestigationModel(SQLiteEngine(str(tmp_path / "b.db")))
    m1.save(make_investigation("inv-001"))
    assert m2.get("inv-001") is None
