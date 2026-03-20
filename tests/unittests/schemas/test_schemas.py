from datetime import datetime
import pytest
from pydantic import ValidationError
from src.schemas.alert import Alert
from src.schemas.incident_report import IncidentReport, Severity, Verdict


VALID_ALERT = {
    "id": "alert-001",
    "type": "brute-force",
    "title": "Multiple failed logins",
    "description": "50 failed login attempts in 5 minutes",
    "severity": "high",
    "source": "splunk",
    "timestamp": "2026-03-13T10:00:00Z",
}


def test_alert_valid():
    alert = Alert.model_validate(VALID_ALERT)
    assert alert.id == "alert-001"
    assert isinstance(alert.timestamp, datetime)


def test_alert_raw_defaults_to_empty_dict():
    alert = Alert.model_validate(VALID_ALERT)
    assert alert.raw == {}


def test_alert_missing_required_field():
    data = {**VALID_ALERT}
    del data["type"]
    with pytest.raises(ValidationError):
        Alert.model_validate(data)


def test_alert_invalid_timestamp():
    data = {**VALID_ALERT, "timestamp": "not-a-date"}
    with pytest.raises(ValidationError):
        Alert.model_validate(data)


def test_incident_report_valid():
    report = IncidentReport(
        alert_id="alert-001",
        severity=Severity.HIGH,
        verdict=Verdict.TRUE_POSITIVE,
        confidence=0.9,
        summary="Confirmed brute force attack.",
        affected_entities=["user@example.com", "1.2.3.4"],
        timeline=["10:00 — 50 failed logins from 1.2.3.4"],
        investigation_steps=["Queried auth logs for failed logins"],
        scope="Single user account potentially compromised",
        findings=["50 failed logins from 1.2.3.4"],
        recommended_actions=["Block IP 1.2.3.4"],
        detection_rule_improvements=[],
        runbook="brute-force",
    )
    assert report.investigation_truncated is False


def test_incident_report_invalid_severity():
    with pytest.raises(ValidationError):
        IncidentReport(
            alert_id="alert-001",
            severity="extreme",
            verdict=Verdict.INCONCLUSIVE,
            confidence=0.0,
            summary="",
            findings=[],
            recommended_actions=[],
            detection_rule_improvements=[],
            runbook="",
        )
