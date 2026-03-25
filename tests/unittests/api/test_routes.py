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
    data = response.json()
    assert data["alert_id"] == "alert-001"
    assert data["status"] == "complete"
    assert data["runbook"] == "generic"
    assert "id" in data
    assert "report" in data


def test_investigate_invalid_payload(client):
    response = client.post("/investigate", json={"id": "alert-001"})
    assert response.status_code == 422


def test_investigate_missing_body(client):
    response = client.post("/investigate")
    assert response.status_code == 422


# GET /investigations
def test_list_investigations_empty(client):
    response = client.get("/investigations")
    assert response.status_code == 200
    assert response.json() == []


def test_list_investigations_after_post(client):
    client.post("/investigate", json=VALID_ALERT)
    response = client.get("/investigations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["alert_id"] == "alert-001"


def test_get_investigation_by_id(client):
    post = client.post("/investigate", json=VALID_ALERT).json()
    investigation_id = post["id"]
    response = client.get(f"/investigations/{investigation_id}")
    assert response.status_code == 200
    assert response.json()["id"] == investigation_id


def test_get_investigation_not_found(client):
    response = client.get("/investigations/unknown-id")
    assert response.status_code == 404


# GET /reports
def test_list_reports_empty(client):
    response = client.get("/reports")
    assert response.status_code == 200
    assert response.json() == []


def test_list_reports_after_post(client):
    client.post("/investigate", json=VALID_ALERT)
    response = client.get("/reports")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["alert_id"] == "alert-001"


def test_get_report_by_investigation_id(client):
    post = client.post("/investigate", json=VALID_ALERT).json()
    investigation_id = post["id"]
    response = client.get(f"/reports/{investigation_id}")
    assert response.status_code == 200
    assert response.json()["alert_id"] == "alert-001"


def test_get_report_not_found(client):
    response = client.get("/reports/unknown-id")
    assert response.status_code == 404


# GET /runbooks
def test_list_runbooks(client):
    response = client.get("/runbooks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(r["name"] == "generic" for r in data)


def test_get_runbook_by_name(client):
    response = client.get("/runbooks/generic")
    assert response.status_code == 200
    assert response.json()["name"] == "generic"


def test_get_runbook_not_found(client):
    response = client.get("/runbooks/nonexistent")
    assert response.status_code == 404


# POST /hunt
def test_hunt_not_implemented(client):
    response = client.post("/hunt")
    assert response.status_code == 501
