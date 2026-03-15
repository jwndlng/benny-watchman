VALID_ALERT = {
    "id": "alert-001",
    "type": "brute-force",
    "title": "Multiple failed logins",
    "description": "50 failed login attempts in 5 minutes",
    "severity": "high",
    "source": "splunk",
    "timestamp": "2026-03-13T10:00:00Z",
}


# POST /investigate
def test_investigate_returns_investigation(client):
    response = client.post("/investigate", json=VALID_ALERT)
    assert response.status_code == 202
    data = response.get_json()
    assert data["alert_id"] == "alert-001"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


def test_investigate_invalid_payload(client):
    response = client.post("/investigate", json={"id": "alert-001"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_investigate_missing_body(client):
    response = client.post("/investigate", content_type="application/json")
    assert response.status_code == 400


# GET /investigations
def test_list_investigations(client):
    response = client.get("/investigations")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_investigation_not_found(client):
    response = client.get("/investigations/unknown-id")
    assert response.status_code == 404


# GET /reports
def test_list_reports(client):
    response = client.get("/reports")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_report_not_found(client):
    response = client.get("/reports/unknown-id")
    assert response.status_code == 404


# GET /runbooks
def test_list_runbooks(client):
    response = client.get("/runbooks")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_runbook_not_found(client):
    response = client.get("/runbooks/brute-force")
    assert response.status_code == 404


# POST /hunt
def test_hunt_not_implemented(client):
    response = client.post("/hunt")
    assert response.status_code == 501
