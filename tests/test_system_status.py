from fastapi.testclient import TestClient

from app.main import app


def test_get_system_status_returns_operational_summary():
    with TestClient(app) as client:
        response = client.get("/system/status")

    assert response.status_code == 200

    payload = response.json()

    assert "provider" in payload
    assert "sport" in payload
    assert "bookmakers" in payload
    assert "scheduler" in payload
    assert "alerts" in payload
    assert "telegram" in payload
    assert "database_counts" in payload

    assert "enabled" in payload["scheduler"]
    assert "configured" in payload["telegram"]
    assert "events" in payload["database_counts"]
    assert "odds_snapshots" in payload["database_counts"]
    assert "alerts" in payload["database_counts"]
    assert "notification_logs" in payload["database_counts"]
