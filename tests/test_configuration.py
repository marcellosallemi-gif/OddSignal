from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_configuration_available_competitions_returns_list():
    with TestClient(app) as client:
        response = client.get("/configuration/available-competitions")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_monitored_competition():
    competition_name = "Test League " + uuid4().hex

    payload = {
        "competition_name": competition_name,
        "country": "Test",
        "provider": "odds_api_io",
        "provider_league_slug": "test-league-" + uuid4().hex,
        "is_active": True,
    }

    with TestClient(app) as client:
        response = client.post(
            "/configuration/monitored-competitions",
            json=payload,
        )

    assert response.status_code == 200

    data = response.json()
    assert data["competition_name"] == competition_name
    assert data["provider_league_slug"] == payload["provider_league_slug"]
    assert data["is_active"] is True


def test_create_notification_recipient():
    payload = {
        "channel": "telegram",
        "recipient_value": "123456789",
        "label": "Test Telegram",
        "is_active": True,
    }

    with TestClient(app) as client:
        response = client.post(
            "/configuration/notification-recipients",
            json=payload,
        )

    assert response.status_code == 200

    data = response.json()
    assert data["channel"] == "telegram"
    assert data["recipient_value"] == "123456789"
    assert data["is_active"] is True


def test_notification_recipient_upsert_prevents_duplicates():
    payload = {
        "channel": "telegram",
        "recipient_value": "duplicate-chat-id",
        "label": "First Label",
        "is_active": True,
    }

    with TestClient(app) as client:
        first_response = client.post(
            "/configuration/notification-recipients",
            json=payload,
        )

        second_response = client.post(
            "/configuration/notification-recipients",
            json={
                **payload,
                "label": "Updated Label",
                "is_active": False,
            },
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    assert second_data["id"] == first_data["id"]
    assert second_data["label"] == "Updated Label"
    assert second_data["is_active"] is False
