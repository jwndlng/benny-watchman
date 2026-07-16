"""Unit tests for ElasticsearchEngine."""

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.engines.elasticsearch import ElasticsearchEngine


@pytest.fixture
def engine():
    with patch("src.adapters.engines.elasticsearch.Elasticsearch") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        eng = ElasticsearchEngine(host="https://es:9200", api_key="key")
        eng._client = mock_client
        yield eng, mock_client


@pytest.fixture
def engine_with_pattern():
    with patch("src.adapters.engines.elasticsearch.Elasticsearch") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        eng = ElasticsearchEngine(host="https://es:9200", api_key="key", index_pattern="logs-*")
        eng._client = mock_client
        yield eng, mock_client


# --- list_tables ---


@pytest.mark.anyio
async def test_list_tables_no_pattern_excludes_hidden(engine):
    eng, client = engine
    client.field_caps.return_value = {
        "indices": ["logs-2025.05.01", ".kibana", "audit-2025.05.01"],
        "fields": {},
    }
    tables = await eng.list_tables()
    names = [t.name for t in tables]
    assert "logs-2025.05.01" in names
    assert "audit-2025.05.01" in names
    assert ".kibana" not in names


@pytest.mark.anyio
async def test_list_tables_with_pattern_uses_pattern(engine_with_pattern):
    eng, client = engine_with_pattern
    client.field_caps.return_value = {
        "indices": ["logs-2025.05.01", "logs-2025.05.02"],
        "fields": {},
    }
    tables = await eng.list_tables()
    call_kwargs = client.field_caps.call_args
    assert call_kwargs.kwargs.get("index") == "logs-*"
    assert len(tables) == 2


@pytest.mark.anyio
async def test_list_tables_returns_sorted_unique(engine):
    eng, client = engine
    client.field_caps.return_value = {
        "indices": ["b-index", "a-index", "a-index"],
        "fields": {},
    }
    tables = await eng.list_tables()
    names = [t.name for t in tables]
    assert names == sorted(names)
    assert len(names) == len(set(names))


# --- get_schema ---


@pytest.mark.anyio
async def test_get_schema_returns_column_info(engine):
    eng, client = engine
    client.field_caps.return_value = {
        "indices": ["logs-2025.05.01"],
        "fields": {
            "@timestamp": {"date": {"type": "date", "metadata_field": False}},
            "user.name": {"keyword": {"type": "keyword", "metadata_field": False}},
        },
    }
    cols = await eng.get_schema("logs-2025.05.01")
    col_map = {c.name: c for c in cols}
    assert "@timestamp" in col_map
    assert col_map["@timestamp"].type == "date"
    assert col_map["user.name"].notnull is False
    assert col_map["user.name"].pk is False


@pytest.mark.anyio
async def test_get_schema_handles_empty_fields(engine):
    eng, client = engine
    client.field_caps.return_value = {"indices": ["myindex"], "fields": {}}
    cols = await eng.get_schema("myindex")
    assert cols == []


# --- get_sample ---


@pytest.mark.anyio
async def test_get_sample_returns_rows(engine):
    eng, client = engine
    client.esql.query.return_value = {
        "columns": [{"name": "@timestamp"}, {"name": "user.name"}],
        "values": [["2025-05-01", "alice"], ["2025-05-02", "bob"]],
    }
    rows = await eng.get_sample("logs-*", n=2)
    assert len(rows) == 2
    assert rows[0]["@timestamp"] == "2025-05-01"
    assert rows[1]["user.name"] == "bob"


@pytest.mark.anyio
async def test_get_sample_empty_index(engine):
    eng, client = engine
    client.esql.query.return_value = {"columns": [], "values": []}
    rows = await eng.get_sample("empty-index")
    assert rows == []


# --- run_query ---


@pytest.mark.anyio
async def test_run_query_appends_limit_when_absent(engine):
    eng, client = engine
    client.esql.query.return_value = {"columns": [], "values": []}
    await eng.run_query('FROM logs-* | WHERE event.category == "auth"')
    query_sent = client.esql.query.call_args.kwargs["body"]["query"]
    assert "| LIMIT 500" in query_sent


@pytest.mark.anyio
async def test_run_query_does_not_double_limit(engine):
    eng, client = engine
    client.esql.query.return_value = {"columns": [], "values": []}
    await eng.run_query("FROM logs-* | LIMIT 100")
    query_sent = client.esql.query.call_args.kwargs["body"]["query"]
    assert query_sent.count("LIMIT") == 1


@pytest.mark.anyio
async def test_run_query_limit_case_insensitive(engine):
    eng, client = engine
    client.esql.query.return_value = {"columns": [], "values": []}
    await eng.run_query("FROM logs-* | limit 50")
    query_sent = client.esql.query.call_args.kwargs["body"]["query"]
    assert "| LIMIT 500" not in query_sent


@pytest.mark.anyio
async def test_run_query_returns_dicts(engine):
    eng, client = engine
    client.esql.query.return_value = {
        "columns": [{"name": "user.name"}, {"name": "count"}],
        "values": [["alice", 5], ["bob", 3]],
    }
    rows = await eng.run_query("FROM logs-* | STATS count = COUNT(*) BY user.name | LIMIT 10")
    assert rows == [
        {"user.name": "alice", "count": 5},
        {"user.name": "bob", "count": 3},
    ]


# --- close ---


@pytest.mark.anyio
async def test_close_calls_client_close(engine):
    eng, client = engine
    await eng.close()
    client.close.assert_called_once()
