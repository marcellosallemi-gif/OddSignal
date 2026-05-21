import os

from fastapi.testclient import TestClient

from app.main import app


def enable_auth(monkeypatch):
    monkeypatch.setenv("APP_AUTH_ENABLED", "1")
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("APP_USERNAME", "admin")
    monkeypatch.setenv("APP_PASSWORD", "secret")
    monkeypatch.setenv("APP_SESSION_SECRET", "test-session-secret")


def login(client):
    return client.post(
        "/login",
        data={
            "username": "admin",
            "password": "secret",
        },
        follow_redirects=False,
    )


def test_dashboard_without_session_redirects_to_login(monkeypatch):
    enable_auth(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_page_is_public(monkeypatch):
    enable_auth(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/login")

    assert response.status_code == 200
    assert "OddSignal" in response.text
    assert "Accedi" in response.text


def test_login_rejects_wrong_credentials(monkeypatch):
    enable_auth(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "wrong",
            },
        )

    assert response.status_code == 401
    assert "Credenziali non valide" in response.text


def test_login_sets_cookie_and_allows_dashboard(monkeypatch):
    enable_auth(monkeypatch)

    with TestClient(app) as client:
        login_response = login(client)
        dashboard_response = client.get("/")

    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/"
    assert "oddsignal_session=" in login_response.headers["set-cookie"]
    assert "HttpOnly" in login_response.headers["set-cookie"]
    assert "SameSite=lax" in login_response.headers["set-cookie"]
    assert dashboard_response.status_code == 200
    assert "OddSignal" in dashboard_response.text


def test_logout_clears_cookie_and_redirects_to_login(monkeypatch):
    enable_auth(monkeypatch)

    with TestClient(app) as client:
        login(client)
        logout_response = client.get("/logout", follow_redirects=False)
        dashboard_response = client.get("/", follow_redirects=False)

    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login"
    assert "oddsignal_session=" in logout_response.headers["set-cookie"]
    assert "Max-Age=0" in logout_response.headers["set-cookie"]
    assert dashboard_response.status_code == 303
    assert dashboard_response.headers["location"] == "/login"


def test_health_is_public_when_auth_enabled(monkeypatch):
    enable_auth(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_static_logo_is_public_when_auth_enabled(monkeypatch):
    enable_auth(monkeypatch)

    logo_path = "app/static/brand/oddsignal-horizontal.png"
    if not os.path.exists(logo_path):
        return

    with TestClient(app) as client:
        response = client.get("/static/brand/oddsignal-horizontal.png")

    assert response.status_code == 200


def test_operational_api_requires_session_when_enabled(monkeypatch):
    enable_auth(monkeypatch)

    with TestClient(app) as client:
        unauthenticated = client.get("/system/readiness", follow_redirects=False)
        login(client)
        authenticated = client.get("/system/readiness")

    assert unauthenticated.status_code == 303
    assert unauthenticated.headers["location"] == "/login"
    assert authenticated.status_code == 200
