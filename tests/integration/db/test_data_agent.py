"""DB integration tests for DataSQLiteAgent against the seeded dataset.

These tests require no LLM calls — they verify that the seeded DB is queryable
and that the expected scenario data is present.
"""

from tests.harness.seeder.synthetic_db import (
    BRUTE_FORCE_ATTACKER_IP,
    BRUTE_FORCE_MIN_FAILURES,
)


def test_list_tables(data_agent):
    tables = data_agent.list_tables()
    names = {t.name for t in tables}
    assert "auth_logs" in names
    assert "network_flows" in names


def test_brute_force_scenario_planted(data_agent):
    rows = data_agent.run_query(
        f"SELECT count(*) AS cnt FROM auth_logs "
        f"WHERE src_ip = '{BRUTE_FORCE_ATTACKER_IP}' AND success = 0"
    )
    assert rows[0]["cnt"] >= BRUTE_FORCE_MIN_FAILURES


def test_schema_context_injected(data_agent):
    assert "auth_logs" in data_agent.instructions
