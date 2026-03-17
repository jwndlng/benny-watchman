"""Synthetic security log dataset — generates reproducible SQLite data.

Generates two tables — auth_logs and network_flows — with realistic-looking
background traffic plus a planted brute-force scenario for golden tests.

Usage (CLI):
    uv run python tests/harness/seeder/synthetic_db.py [--db-path PATH] [--rows N] [--seed INT] [--reset]

Importable:
    from tests.harness.seeder.synthetic_db import SyntheticDataset, seed_database
"""

import argparse
import random
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

from tests.harness.seeder.base_dataset import BaseDataset

# ---------------------------------------------------------------------------
# Planted scenario constants — referenced by integration tests and cases
# ---------------------------------------------------------------------------
BRUTE_FORCE_ATTACKER_IP = "192.0.2.99"
BRUTE_FORCE_TARGET_USER = "admin"
BRUTE_FORCE_TARGET_HOST = "auth.internal"
BRUTE_FORCE_MIN_FAILURES = 80

# ---------------------------------------------------------------------------
# Background data pools
# ---------------------------------------------------------------------------
_USERS = ["alice", "bob", "carol", "dave", "eve", "frank", "grace", "henry"]
_HOSTS = ["auth.internal", "vpn.internal", "mail.internal", "ssh.internal"]
_INTERNAL_SUBNETS = ["10.0.0.", "10.0.1.", "192.168.1.", "172.16.0."]
_EXTERNAL_PREFIXES = ["203.0.113.", "198.51.100.", "185.220.101.", "45.33.32."]
_PROTOCOLS = ["TCP", "UDP"]
_DIRECTIONS = ["inbound", "outbound", "internal"]
_COMMON_PORTS = [22, 80, 443, 3389, 8080, 8443, 53, 445, 3306]


def _random_ip(rng: random.Random, internal: bool = True) -> str:
    prefix = rng.choice(_INTERNAL_SUBNETS if internal else _EXTERNAL_PREFIXES)
    return prefix + str(rng.randint(1, 254))


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS auth_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    username    TEXT    NOT NULL,
    src_ip      TEXT    NOT NULL,
    dst_host    TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    success     INTEGER NOT NULL,
    session_id  TEXT
);

CREATE TABLE IF NOT EXISTS network_flows (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    src_ip      TEXT    NOT NULL,
    dst_ip      TEXT    NOT NULL,
    dst_port    INTEGER NOT NULL,
    protocol    TEXT    NOT NULL,
    bytes_sent  INTEGER NOT NULL,
    bytes_recv  INTEGER NOT NULL,
    direction   TEXT    NOT NULL
);
"""


def _drop_tables(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS auth_logs")
    conn.execute("DROP TABLE IF EXISTS network_flows")
    conn.commit()


# ---------------------------------------------------------------------------
# Row generators
# ---------------------------------------------------------------------------
def _generate_auth_logs(
    rng: random.Random, rows: int, base_time: datetime
) -> list[tuple]:
    records = []

    # Background traffic — 80% of rows
    bg_count = int(rows * 0.8)
    for i in range(bg_count):
        ts = base_time + timedelta(seconds=rng.randint(0, 86400))
        user = rng.choice(_USERS)
        src_ip = _random_ip(rng, internal=rng.random() > 0.3)
        host = rng.choice(_HOSTS)
        success = 1 if rng.random() < 0.9 else 0
        event_type = "login_success" if success else "login_failure"
        session_id = str(uuid.UUID(int=rng.getrandbits(128))) if success else None
        records.append((ts, user, src_ip, host, event_type, success, session_id))

    # Planted brute-force scenario — 20% of rows
    # Attacker hammers admin with failures in a 5-minute window, then succeeds
    attack_start = base_time + timedelta(hours=rng.randint(1, 20))
    failure_count = rng.randint(BRUTE_FORCE_MIN_FAILURES, BRUTE_FORCE_MIN_FAILURES + 20)
    for i in range(failure_count):
        ts = attack_start + timedelta(seconds=i * 3)  # one attempt every ~3s
        records.append(
            (
                ts,
                BRUTE_FORCE_TARGET_USER,
                BRUTE_FORCE_ATTACKER_IP,
                BRUTE_FORCE_TARGET_HOST,
                "login_failure",
                0,
                None,
            )
        )
    # Successful login after the brute force
    success_ts = attack_start + timedelta(seconds=failure_count * 3 + 10)
    records.append(
        (
            success_ts,
            BRUTE_FORCE_TARGET_USER,
            BRUTE_FORCE_ATTACKER_IP,
            BRUTE_FORCE_TARGET_HOST,
            "login_success",
            1,
            str(uuid.UUID(int=rng.getrandbits(128))),
        )
    )

    rng.shuffle(records)
    return [(_iso(ts),) + tuple(rest) for ts, *rest in records]


def _generate_network_flows(
    rng: random.Random, rows: int, base_time: datetime
) -> list[tuple]:
    records = []
    for _ in range(rows):
        ts = base_time + timedelta(seconds=rng.randint(0, 86400))
        direction = rng.choice(_DIRECTIONS)
        if direction == "inbound":
            src_ip = _random_ip(rng, internal=False)
            dst_ip = _random_ip(rng, internal=True)
        elif direction == "outbound":
            src_ip = _random_ip(rng, internal=True)
            dst_ip = _random_ip(rng, internal=False)
        else:
            src_ip = _random_ip(rng, internal=True)
            dst_ip = _random_ip(rng, internal=True)
        dst_port = rng.choice(_COMMON_PORTS)
        protocol = rng.choice(_PROTOCOLS)
        bytes_sent = rng.randint(64, 1_000_000)
        bytes_recv = rng.randint(64, 1_000_000)
        records.append(
            (
                _iso(ts),
                src_ip,
                dst_ip,
                dst_port,
                protocol,
                bytes_sent,
                bytes_recv,
                direction,
            )
        )
    return records


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def seed_database(
    db_path: str, rows: int = 500, seed: int = 42, reset: bool = False
) -> None:
    """Create and populate the dataset database.

    Safe to call from pytest fixtures — no side effects beyond writing to db_path.
    """
    rng = random.Random(seed)
    base_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    conn = sqlite3.connect(db_path)
    try:
        if reset:
            _drop_tables(conn)
        conn.executescript(_SCHEMA)

        auth_rows = _generate_auth_logs(rng, rows, base_time)
        conn.executemany(
            "INSERT INTO auth_logs (ts, username, src_ip, dst_host, event_type, success, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            auth_rows,
        )

        flow_rows = _generate_network_flows(rng, rows, base_time)
        conn.executemany(
            "INSERT INTO network_flows (ts, src_ip, dst_ip, dst_port, protocol, bytes_sent, bytes_recv, direction) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            flow_rows,
        )

        conn.commit()
        print(
            f"Seeded {len(auth_rows)} auth_logs and {len(flow_rows)} network_flows into {db_path}"
        )
    finally:
        conn.close()


class SyntheticDataset(BaseDataset):
    """Generates a reproducible synthetic security log dataset."""

    def __init__(self, rows: int = 500, seed: int = 42) -> None:
        self.rows = rows
        self.seed = seed

    def load(self, db_path: str) -> None:
        seed_database(db_path, rows=self.rows, seed=self.seed, reset=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed SQLite DB with synthetic security logs"
    )
    parser.add_argument(
        "--db-path", default="data.db", help="Path to SQLite database file"
    )
    parser.add_argument(
        "--rows", type=int, default=500, help="Approximate rows per table"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Drop and recreate tables first"
    )
    args = parser.parse_args()

    seed_database(args.db_path, rows=args.rows, seed=args.seed, reset=args.reset)
