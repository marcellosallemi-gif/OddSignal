import base64
import os

from fastapi.testclient import TestClient

from app.main import app


def auth_header(username: str, password: str):
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_dashboard_requires_auth_when_enabled(monkeypatch):
    monkeypatch.setenv("APP_AUTH_ENABLED", "1")
    monkeypatch.setenv("APP_USERNAME", "admin")
    monkeypatch.setenv("APP_PASSWORD", "secret")

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Basic realm="OddSignal"'


def test_dashboard_rejects_wrong_auth_when_enabled(monkeypatch):
    monkeypatch.setenv("APP_AUTH_ENABLED", "1")
    monkeypatch.setenv("APP_USERNAME", "admin")
    monkeypatch.setenv("APP_PASSWORD", "secret")

    with TestClient(app) as client:
        response = client.get("/", headers=auth_header("admin", "wrong"))

    assert response.status_code == 401


def test_dashboard_accepts_correct_auth_when_enabled(monkeypatch):
    monkeypatch.setenv("APP_AUTH_ENABLED", "1")
    monkeypatch.setenv("APP_USERNAME", "admin")
    monkeypatch.setenv("APP_PASSWORD", "secret")

    with TestClient(app) as client:
        response = client.get("/", headers=auth_header("admin", "secret"))

    assert response.status_code == 200
    assert "OddSignal" in response.text


def test_health_is_public_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("APP_AUTH_ENABLED", "1")
    monkeypatch.setenv("APP_USERNAME", "admin")
    monkeypatch.setenv("APP_PASSWORD", "secret")

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_static_logo_is_public_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("APP_AUTH_ENABLED", "1")
    monkeypatch.setenv("APP_USERNAME", "admin")
    monkeypatch.setenv("APP_PASSWORD", "secret")

    logo_path = "app/static/brand/oddsignal-horizontal.png"
    if not os.path.exists(logo_path):
        return

    with TestClient(app) as client:
        response = client.get("/static/brand/oddsignal-horizontal.png")

    assert response.status_code == 200


def test_operational_api_requires_auth_when_enabled(monkeypatch):
    monkeypatch.setenv("APP_AUTH_ENABLED", "1")
    monkeypatch.setenv("APP_USERNAME", "admin")
    monkeypatch.setenv("APP_PASSWORD", "secret")

    with TestClient(app) as client:
        unauthenticated = client.get("/system/readiness")
        authenticated = client.get(
            "/system/readiness",
            headers=auth_header("admin", "secret"),
        )

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200
