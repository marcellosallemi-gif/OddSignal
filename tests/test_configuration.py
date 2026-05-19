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


def test_get_monitored_markets_returns_list():
    with TestClient(app) as client:
        response = client.get("/configuration/monitored-markets")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_monitored_market():
    market_name = "Test Market " + uuid4().hex

    with TestClient(app) as client:
        response = client.post(
            "/configuration/monitored-markets",
            json={
                "market_name": market_name,
                "is_active": True,
            },
        )

    assert response.status_code == 200

    data = response.json()
    assert data["market_name"] == market_name
    assert data["is_active"] is True


def test_toggle_monitored_market():
    market_name = "Toggle Market " + uuid4().hex

    with TestClient(app) as client:
        create_response = client.post(
            "/configuration/monitored-markets",
            json={
                "market_name": market_name,
                "is_active": True,
            },
        )
        market_id = create_response.json()["id"]

        toggle_response = client.patch(
            f"/configuration/monitored-markets/{market_id}/toggle?is_active=false"
        )

    assert create_response.status_code == 200
    assert toggle_response.status_code == 200
    assert toggle_response.json()["is_active"] is False


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


def test_get_alert_settings():
    with TestClient(app) as client:
        response = client.get("/configuration/alert-settings")

    assert response.status_code == 200

    data = response.json()
    assert "min_percent" in data
    assert "max_percent" in data
    assert "critical_percent" in data
    assert "deduplication_minutes" in data


def test_update_alert_settings():
    payload = {
        "min_percent": 8,
        "max_percent": 15,
        "critical_percent": 15,
        "deduplication_minutes": 30,
    }

    with TestClient(app) as client:
        response = client.put(
            "/configuration/alert-settings",
            json=payload,
        )

    assert response.status_code == 200

    data = response.json()
    assert data["min_percent"] == 8
    assert data["max_percent"] == 15
    assert data["critical_percent"] == 15
    assert data["deduplication_minutes"] == 30


def test_update_alert_settings_rejects_invalid_range():
    payload = {
        "min_percent": 15,
        "max_percent": 8,
        "critical_percent": 15,
        "deduplication_minutes": 30,
    }

    with TestClient(app) as client:
        response = client.put(
            "/configuration/alert-settings",
            json=payload,
        )

    assert response.status_code == 400
