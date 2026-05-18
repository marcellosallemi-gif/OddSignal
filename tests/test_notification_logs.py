from fastapi.testclient import TestClient

from app.main import app


def test_get_notification_logs_returns_list():
    with TestClient(app) as client:
        response = client.get("/notification-logs")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
