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


def test_system_readiness_returns_operational_checks():
    with TestClient(app) as client:
        response = client.get("/system/readiness")

    assert response.status_code == 200
    payload = response.json()

    assert "ready" in payload
    assert "automatic_monitoring_ready" in payload
    assert "scheduler_enabled" in payload
    assert "checks" in payload
    assert "issues" in payload
    assert "warnings" in payload

    checks = payload["checks"]

    assert "provider_plan" in checks
    assert "bookmakers" in checks
    assert "competitions" in checks
    assert "markets" in checks
    assert "telegram" in checks
    assert "scheduler" in checks

    assert "ok" in checks["provider_plan"]
    assert "ok" in checks["bookmakers"]
    assert "ok" in checks["competitions"]
    assert "ok" in checks["markets"]
    assert "ok" in checks["telegram"]
    assert "enabled" in checks["scheduler"]


def test_provider_usage_returns_usage_status():
    with TestClient(app) as client:
        response = client.get("/system/provider-usage")

    assert response.status_code == 200
    payload = response.json()

    assert payload["provider"] == "odds_api_io"
    assert "hourly_request_limit" in payload
    assert "requests_used_last_hour" in payload
    assert "requests_remaining" in payload
    assert "limit_reached" in payload
    assert "message" in payload
