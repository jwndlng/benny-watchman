"""Synthetic asset/vulnerability inventory — reproducible SQLite data for VM dev/tests.

Two tables — assets (inventory) and vulnerabilities (scanner findings) — including
a planted internet-facing RCE on host-01 (CVE-2024-1234) referenced by tests.

Usage (CLI):
    uv run python tests/harness/seeder/asset_db.py [--db-path PATH] [--reset]

Importable:
    from tests.harness.seeder.asset_db import AssetDataset
"""

import argparse
import sqlite3

PLANTED_CVE = "CVE-2024-1234"
PLANTED_ASSET = "host-01"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    asset            TEXT PRIMARY KEY,
    hostname         TEXT NOT NULL,
    environment      TEXT NOT NULL,
    internet_facing  INTEGER NOT NULL,
    owner            TEXT NOT NULL,
    os               TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id      TEXT PRIMARY KEY,
    cve     TEXT NOT NULL,
    asset   TEXT NOT NULL,
    cvss    REAL NOT NULL,
    kev     INTEGER NOT NULL,
    status  TEXT NOT NULL
);
"""

_ASSETS = [
    ("host-01", "web-prod-01", "production", 1, "platform-team", "Ubuntu 22.04"),
    ("host-02", "db-prod-01", "production", 0, "data-team", "Ubuntu 22.04"),
    ("host-03", "build-ci-01", "ci", 0, "devex-team", "Debian 12"),
]
_VULNS = [
    ("vuln-001", PLANTED_CVE, "host-01", 9.8, 1, "open"),
    ("vuln-002", "CVE-2023-5555", "host-02", 6.5, 0, "open"),
    ("vuln-003", "CVE-2022-1111", "host-03", 4.2, 0, "mitigated"),
]


class AssetDataset:
    """Seeds a SQLite asset/vulnerability inventory."""

    def __init__(self, reset: bool = True) -> None:
        self._reset = reset

    def load(self, db_path: str) -> None:
        """Create the schema and insert the synthetic rows into db_path."""
        conn = sqlite3.connect(db_path)
        try:
            if self._reset:
                conn.executescript(
                    "DROP TABLE IF EXISTS assets; DROP TABLE IF EXISTS vulnerabilities;"
                )
            conn.executescript(_SCHEMA)
            conn.executemany("INSERT INTO assets VALUES (?,?,?,?,?,?)", _ASSETS)
            conn.executemany("INSERT INTO vulnerabilities VALUES (?,?,?,?,?,?)", _VULNS)
            conn.commit()
        finally:
            conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="vuln.db")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    AssetDataset(reset=args.reset).load(args.db_path)


if __name__ == "__main__":
    main()
