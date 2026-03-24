"""Unit tests for SQLiteEngine."""

import pytest

from src.engines.sqlite import SQLiteEngine


@pytest.fixture
def engine(tmp_path):
    """In-memory SQLiteEngine with a populated test table."""
    db = SQLiteEngine(str(tmp_path / "test.db"))
    conn = db._conn
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, name TEXT NOT NULL, count INTEGER)")
    conn.execute("INSERT INTO events VALUES (1, 'login', 10)")
    conn.execute("INSERT INTO events VALUES (2, 'logout', 5)")
    conn.commit()
    return db


# --- list_tables ---

def test_list_tables_returns_table(engine):
    names = [t.name for t in engine.list_tables()]
    assert "events" in names


def test_list_tables_empty_db(tmp_path):
    db = SQLiteEngine(str(tmp_path / "empty.db"))
    assert db.list_tables() == []


# --- get_schema ---

def test_get_schema_columns(engine):
    cols = {c.name: c for c in engine.get_schema("events")}
    assert set(cols) == {"id", "name", "count"}
    assert cols["id"].pk is True
    assert cols["name"].notnull is True


def test_get_schema_invalid_table_raises(engine):
    with pytest.raises(ValueError, match="Invalid table name"):
        engine.get_schema("bad; DROP TABLE events--")


# --- get_sample ---

def test_get_sample_returns_rows(engine):
    rows = engine.get_sample("events", n=2)
    assert len(rows) == 2
    assert rows[0]["name"] == "login"


def test_get_sample_respects_limit(engine):
    rows = engine.get_sample("events", n=1)
    assert len(rows) == 1


def test_get_sample_invalid_table_raises(engine):
    with pytest.raises(ValueError):
        engine.get_sample("bad table!")


# --- run_query ---

def test_run_query_filters(engine):
    rows = engine.run_query("SELECT name, count FROM events WHERE count > 7")
    assert len(rows) == 1
    assert rows[0]["name"] == "login"


def test_run_query_auto_adds_limit(engine):
    # Query without LIMIT should still execute without error
    rows = engine.run_query("SELECT id, name FROM events")
    assert len(rows) == 2


def test_run_query_strips_second_statement(engine):
    # Only first statement should run; second is silently dropped
    rows = engine.run_query("SELECT id, name FROM events; DROP TABLE events")
    assert len(rows) == 2
    assert [t.name for t in engine.list_tables() if t.name == "events"] == ["events"]


# --- key-value store ---

def test_init_store_creates_table(tmp_path):
    db = SQLiteEngine(str(tmp_path / "kv.db"))
    db.init_store("my_store")
    names = [t.name for t in db.list_tables()]
    assert "my_store" in names


def test_init_store_is_idempotent(tmp_path):
    db = SQLiteEngine(str(tmp_path / "kv.db"))
    db.init_store("my_store")
    db.init_store("my_store")  # should not raise


def test_upsert_and_fetch(tmp_path):
    db = SQLiteEngine(str(tmp_path / "kv.db"))
    db.init_store("store")
    db.upsert("store", "abc", '{"value": 1}')
    assert db.fetch("store", "abc") == '{"value": 1}'


def test_fetch_missing_returns_none(tmp_path):
    db = SQLiteEngine(str(tmp_path / "kv.db"))
    db.init_store("store")
    assert db.fetch("store", "missing") is None


def test_upsert_replaces_existing(tmp_path):
    db = SQLiteEngine(str(tmp_path / "kv.db"))
    db.init_store("store")
    db.upsert("store", "x", '{"v": 1}')
    db.upsert("store", "x", '{"v": 2}')
    assert db.fetch("store", "x") == '{"v": 2}'


def test_fetch_all_returns_all(tmp_path):
    db = SQLiteEngine(str(tmp_path / "kv.db"))
    db.init_store("store")
    db.upsert("store", "a", '"one"')
    db.upsert("store", "b", '"two"')
    results = db.fetch_all("store")
    assert set(results) == {'"one"', '"two"'}


def test_fetch_all_empty(tmp_path):
    db = SQLiteEngine(str(tmp_path / "kv.db"))
    db.init_store("store")
    assert db.fetch_all("store") == []


# --- schema_context ---

def test_schema_context_contains_table_and_columns(engine):
    ctx = engine.schema_context()
    assert "events" in ctx
    assert "name" in ctx
    assert "count" in ctx


def test_schema_context_empty_db(tmp_path):
    db = SQLiteEngine(str(tmp_path / "empty.db"))
    assert "No tables found" in db.schema_context()
