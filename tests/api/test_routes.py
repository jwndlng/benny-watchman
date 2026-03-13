VALID_ALERT = {
    "id": "alert-001",
    "type": "brute-force",
    "title": "Multiple failed logins",
    "description": "50 failed login attempts in 5 minutes",
    "severity": "high",
    "source": "splunk",
    "timestamp": "2026-03-13T10:00:00Z",
}


def test_investigate_returns_incident_report(client):
    response = client.post("/investigate", json=VALID_ALERT)
    assert response.status_code == 202
    data = response.get_json()
    assert data["alert_id"] == "alert-001"
    assert data["verdict"] == "inconclusive"
    assert "findings" in data
    assert "recommended_actions" in data


def test_investigate_invalid_payload(client):
    response = client.post("/investigate", json={"id": "alert-001"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_investigate_missing_body(client):
    response = client.post("/investigate", content_type="application/json")
    assert response.status_code == 400


def test_list_runbooks(client):
    response = client.get("/runbooks")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_investigation_not_implemented(client):
    response = client.get("/investigations/alert-001")
    assert response.status_code == 501
