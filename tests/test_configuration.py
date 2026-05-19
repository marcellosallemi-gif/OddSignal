from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


class FakeProviderCompetitionRefresh:
    bookmakers = "Stake,Sbobet"

    def get_events(self, limit=10, bookmaker=None):
        return [
            {
                "league": {
                    "name": "Provider Test League",
                    "slug": "provider-test-league",
                },
            },
            {
                "league": {
                    "name": "Provider Test League",
                    "slug": "provider-test-league",
                },
            },
        ]

    def normalize_event(self, event):
        league = event["league"]
        return {
            "league_name": league["name"],
            "league_slug": league["slug"],
        }


class FailingProviderCompetitionRefresh:
    bookmakers = "Stake,Sbobet"

    def get_events(self, limit=10, bookmaker=None):
        raise RuntimeError("League not found")


class RateLimitProviderCompetitionRefresh:
    bookmakers = "Stake,Sbobet"

    def get_events(self, limit=10, bookmaker=None):
        raise RuntimeError("Odds-API.io rate limit reached.")


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


def test_refresh_provider_competitions_upserts_available_competition(monkeypatch):
    from app.routers import configuration

    monkeypatch.setattr(
        configuration,
        "OddsApiIoProvider",
        lambda: FakeProviderCompetitionRefresh(),
    )

    with TestClient(app) as client:
        refresh_response = client.post(
            "/configuration/provider-competitions/refresh?limit=10"
        )
        available_response = client.get("/configuration/available-competitions")

    assert refresh_response.status_code == 200

    data = refresh_response.json()
    assert data["provider"] == "odds_api_io"
    assert data["events_received"] == 2
    assert data["competitions_found"] == 1
    assert data["competitions_upserted"] == 1
    assert data["competitions"][0]["name"] == "Provider Test League"
    assert data["competitions"][0]["provider_league_slug"] == "provider-test-league"

    assert available_response.status_code == 200
    available_competitions = available_response.json()
    refreshed_competition = [
        item
        for item in available_competitions
        if item["name"] == "Provider Test League"
    ][0]
    assert refreshed_competition["provider_league_slug"] == "provider-test-league"




def test_refresh_provider_competitions_returns_429_on_rate_limit(monkeypatch):
    from app.routers import configuration

    monkeypatch.setattr(
        configuration,
        "OddsApiIoProvider",
        lambda: RateLimitProviderCompetitionRefresh(),
    )

    with TestClient(app) as client:
        response = client.post("/configuration/provider-competitions/refresh?limit=10")

    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "provider_rate_limit"


def test_refresh_provider_competitions_returns_404_on_league_not_found(monkeypatch):
    from app.routers import configuration

    monkeypatch.setattr(
        configuration,
        "OddsApiIoProvider",
        lambda: FailingProviderCompetitionRefresh(),
    )

    with TestClient(app) as client:
        response = client.post("/configuration/provider-competitions/refresh?limit=10")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "provider_league_not_found"
    assert "Campionato non trovato" in response.json()["detail"]["message"]


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


class FakeTelegramResponse:
    status_code = 200

    def json(self):
        private_chat_update = {
            "message": {
                "chat": {
                    "id": 987654321,
                    "type": "private",
                    "first_name": "Mario",
                    "last_name": "Rossi",
                    "username": "mariorossi",
                }
            }
        }

        return {
            "ok": True,
            "result": [
                private_chat_update,
                private_chat_update,
            ],
        }


def test_sync_telegram_recipients_detects_private_chat(monkeypatch):
    from app.routers import configuration

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(
        configuration.httpx,
        "get",
        lambda *args, **kwargs: FakeTelegramResponse(),
    )

    with TestClient(app) as client:
        response = client.post("/configuration/telegram-recipients/sync")

    assert response.status_code == 200
    data = response.json()
    assert data["synced_count"] == 1
    assert data["recipients"][0]["label"] == "Mario Rossi (@mariorossi)"
    assert data["recipients"][0]["is_active"] is False


def test_sync_telegram_recipients_requires_bot_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")

    with TestClient(app) as client:
        response = client.post("/configuration/telegram-recipients/sync")

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "telegram_not_configured"


def test_get_scheduler_settings():
    with TestClient(app) as client:
        response = client.get("/configuration/scheduler-settings")

    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "poll_interval_seconds" in data
    assert "event_limit" in data


def test_update_scheduler_settings_allows_local_short_interval(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("APP_DEBUG", "true")

    payload = {
        "enabled": False,
        "poll_interval_seconds": 3,
        "event_limit": 2,
    }

    with TestClient(app) as client:
        response = client.put(
            "/configuration/scheduler-settings",
            json=payload,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["poll_interval_seconds"] == 3
    assert data["event_limit"] == 2


def test_update_scheduler_settings_rejects_invalid_event_limit():
    payload = {
        "enabled": True,
        "poll_interval_seconds": 300,
        "event_limit": 99,
    }

    with TestClient(app) as client:
        response = client.put(
            "/configuration/scheduler-settings",
            json=payload,
        )

    assert response.status_code == 400
    assert "eventi per ciclo" in response.json()["detail"].lower()



def test_sync_telegram_recipients_preserves_existing_active_recipient(monkeypatch):
    from app.routers import configuration

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(
        configuration.httpx,
        "get",
        lambda *args, **kwargs: FakeTelegramResponse(),
    )

    with TestClient(app) as client:
        create_response = client.post(
            "/configuration/notification-recipients",
            json={
                "channel": "telegram",
                "recipient_value": "987654321",
                "label": "Already Active",
                "is_active": True,
            },
        )

        sync_response = client.post("/configuration/telegram-recipients/sync")

    assert create_response.status_code == 200
    assert sync_response.status_code == 200

    data = sync_response.json()
    assert data["synced_count"] == 1
    assert data["recipients"][0]["is_active"] is True
    assert data["recipients"][0]["label"] == "Mario Rossi (@mariorossi)"


def test_get_provider_plan_settings_returns_usage_estimate():
    with TestClient(app) as client:
        response = client.get("/configuration/provider-plan-settings")

    assert response.status_code == 200
    data = response.json()

    assert data["plan_name"]
    assert data["max_bookmakers"] >= 1
    assert data["usage_estimate"]["poll_interval_seconds"] >= 1
    assert data["usage_estimate"]["event_limit"] >= 1
    assert "estimated_requests_per_hour" in data["usage_estimate"]
    assert "recommendation" in data["usage_estimate"]


def test_update_provider_plan_settings_allows_unlimited_plan():
    payload = {
        "plan_name": "Unlimited",
        "hourly_request_limit": None,
        "max_bookmakers": 10,
    }

    with TestClient(app) as client:
        response = client.put(
            "/configuration/provider-plan-settings",
            json=payload,
        )

    assert response.status_code == 200
    data = response.json()

    assert data["plan_name"] == "Unlimited"
    assert data["hourly_request_limit"] is None
    assert data["max_bookmakers"] == 10
    assert data["usage_estimate"]["exceeds_hourly_limit"] is False


def test_update_provider_plan_settings_rejects_invalid_bookmaker_limit():
    payload = {
        "plan_name": "Invalid",
        "hourly_request_limit": 100,
        "max_bookmakers": 0,
    }

    with TestClient(app) as client:
        response = client.put(
            "/configuration/provider-plan-settings",
            json=payload,
        )

    assert response.status_code == 400
    assert "bookmaker" in response.json()["detail"].lower()
