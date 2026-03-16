"""Brute-force SSH login investigation case."""

from datetime import datetime, timezone

from src.schemas.alert import Alert
from src.schemas.incident_report import Severity, Verdict
from tests.harness.cases.base_case import BaseCase
from tests.harness.seeder.base_dataset import BaseDataset
from tests.harness.seeder.synthetic_db import BRUTE_FORCE_ATTACKER_IP, SyntheticDataset


class BruteForceCase(BaseCase):
    name = "brute_force_ssh"
    runbook_name = "generic"
    expected_verdict = Verdict.TRUE_POSITIVE
    expected_severity = Severity.HIGH

    @property
    def dataset(self) -> BaseDataset:
        return SyntheticDataset()

    def alert(self) -> Alert:
        return Alert(
            id="harness-bf-001",
            type="brute_force",
            title="Brute-force login detected",
            description=(
                f"Multiple failed login attempts detected from {BRUTE_FORCE_ATTACKER_IP} "
                "targeting the admin account. Investigate and determine if this is a true positive."
            ),
            severity="high",
            source="auth_monitor",
            timestamp=datetime.now(timezone.utc),
        )
