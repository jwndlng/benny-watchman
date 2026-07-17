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
    assert data["guidance_source"] is None
    assert "id" in data
    assert "report" in data


def test_investigate_invalid_payload(client):
    response = client.post("/investigate", json={"id": "alert-001"})
    assert response.status_code == 422


def test_investigate_missing_body(client):
    response = client.post("/investigate")
    assert response.status_code == 422


def test_investigate_is_idempotent(client):
    first = client.post("/investigate", json=VALID_ALERT)
    assert first.status_code == 202
    second = client.post("/investigate", json=VALID_ALERT)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    listing = client.get("/investigations").json()
    assert len(listing) == 1


# POST /findings (Vulnerability Management)
VALID_FINDING = {
    "id": "finding-001",
    "type": "remote-code-execution",
    "cve": "CVE-2024-1234",
    "asset": "host-01",
    "cvss": 9.8,
    "title": "RCE in libfoo",
    "description": "Unauthenticated RCE in libfoo < 1.2.3",
    "source": "nessus",
    "detected_at": "2026-03-13T10:00:00Z",
}


def test_triage_finding_returns_investigation(client):
    response = client.post("/findings", json=VALID_FINDING)
    assert response.status_code == 202
    data = response.json()
    assert data["alert_id"] == "finding-001"
    assert data["status"] == "complete"
    assert "id" in data


def test_triage_finding_is_idempotent(client):
    first = client.post("/findings", json=VALID_FINDING)
    assert first.status_code == 202
    second = client.post("/findings", json=VALID_FINDING)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_triage_finding_invalid_payload(client):
    response = client.post("/findings", json={"id": "finding-001"})
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


# GET /modules
def test_list_modules(client):
    response = client.get("/modules")
    assert response.status_code == 200
    data = response.json()
    names = {m["name"] for m in data}
    assert "siem" in names
    assert "vuln_mgmt" in names
    assert all("input_type" in m for m in data)


def test_runbooks_route_is_gone(client):
    assert client.get("/runbooks").status_code == 404


# POST /triage/run
def test_triage_run_over_empty_platform(client):
    response = client.post("/triage/run")
    assert response.status_code == 200
    assert response.json() == {"triaged": 0}


# POST /hunt
def test_hunt_not_implemented(client):
    response = client.post("/hunt")
    assert response.status_code == 501
