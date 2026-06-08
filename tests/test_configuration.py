from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Alert, NotificationRecipient, OddsSnapshot


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


class FakeTennisProviderCompetitionRefresh:
    bookmakers = "Stake,Sbobet"

    def get_events(self, limit=10, bookmaker=None):
        return [
            {
                "league": {
                    "name": "ATP Test Tournament",
                    "slug": "atp-test-tournament",
                },
            }
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
    assert all(item["sport"] == "football" for item in response.json())


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
    assert data["sport"] == "football"
    assert data["provider_league_slug"] == payload["provider_league_slug"]
    assert data["is_active"] is True


def test_create_monitored_tennis_competition():
    competition_name = "Tennis Tournament " + uuid4().hex

    payload = {
        "competition_name": competition_name,
        "country": "Italy",
        "sport": "tennis",
        "provider": "odds_api_io",
        "provider_league_slug": "tennis-tournament-" + uuid4().hex,
        "is_active": True,
    }

    with TestClient(app) as client:
        response = client.post(
            "/configuration/monitored-competitions",
            json=payload,
        )
        available_response = client.get("/configuration/available-competitions?sport=tennis")

    assert response.status_code == 200
    data = response.json()
    assert data["competition_name"] == competition_name
    assert data["sport"] == "tennis"
    assert data["is_active"] is True
    assert available_response.status_code == 200


def test_refresh_provider_competitions_upserts_available_competition(monkeypatch):
    from app.routers import configuration

    monkeypatch.setattr(
        configuration,
        "OddsApiIoProvider",
        lambda **kwargs: FakeProviderCompetitionRefresh(),
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
    assert refreshed_competition["sport"] == "football"


def test_refresh_provider_tennis_competitions_uses_tennis_sport(monkeypatch):
    from app.routers import configuration

    captured_kwargs = {}

    def fake_provider_factory(**kwargs):
        captured_kwargs.update(kwargs)
        return FakeTennisProviderCompetitionRefresh()

    monkeypatch.setattr(configuration, "OddsApiIoProvider", fake_provider_factory)

    with TestClient(app) as client:
        refresh_response = client.post(
            "/configuration/provider-competitions/refresh?limit=10&sport=tennis"
        )
        available_response = client.get("/configuration/available-competitions?sport=tennis")

    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert captured_kwargs["sport"] == "tennis"
    assert data["sport"] == "tennis"
    assert data["competitions"][0]["name"] == "ATP Test Tournament"

    available_competitions = available_response.json()
    tennis_competition = [
        item
        for item in available_competitions
        if item["name"] == "ATP Test Tournament"
    ][0]
    assert tennis_competition["sport"] == "tennis"
    assert tennis_competition["provider_league_slug"] == "atp-test-tournament"




def test_refresh_provider_competitions_returns_429_on_rate_limit(monkeypatch):
    from app.routers import configuration

    monkeypatch.setattr(
        configuration,
        "OddsApiIoProvider",
        lambda **kwargs: RateLimitProviderCompetitionRefresh(),
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
        lambda **kwargs: FailingProviderCompetitionRefresh(),
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


def test_monitored_markets_are_returned_with_canonical_italian_labels():
    with TestClient(app) as client:
        double_chance_response = client.post(
            "/configuration/monitored-markets",
            json={
                "market_name": "Double Chance",
                "is_active": False,
            },
        )
        canonical_response = client.post(
            "/configuration/monitored-markets",
            json={
                "market_name": "Doppia chance",
                "is_active": True,
            },
        )
        draw_no_bet_response = client.post(
            "/configuration/monitored-markets",
            json={
                "market_name": "Draw No Bet",
                "is_active": True,
            },
        )
        list_response = client.get("/configuration/monitored-markets")

    assert double_chance_response.status_code == 200
    assert double_chance_response.json()["market_name"] == "Doppia chance"
    assert canonical_response.status_code == 200
    assert draw_no_bet_response.status_code == 200
    assert draw_no_bet_response.json()["market_name"] == "Pareggio escluso"

    market_names = [item["market_name"] for item in list_response.json()]
    assert market_names.count("Doppia chance") == 1
    assert "Double Chance" not in market_names
    assert "Pareggio escluso" in market_names


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


class FakeTelegramSendResponse:
    status_code = 200
    text = "ok"


class FakeTelegramClient:
    sent_payloads = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json):
        self.sent_payloads.append(
            {
                "url": url,
                "json": json,
            }
        )
        return FakeTelegramSendResponse()


def deactivate_telegram_recipients():
    db = SessionLocal()
    try:
        for recipient in db.query(NotificationRecipient).filter(
            NotificationRecipient.channel == "telegram"
        ):
            recipient.is_active = False
            recipient.status = "disabled"
        db.commit()
    finally:
        db.close()


def create_active_telegram_recipient(recipient_value):
    db = SessionLocal()
    try:
        recipient = NotificationRecipient(
            channel="telegram",
            recipient_value=recipient_value,
            label="Test Telegram",
            is_active=True,
            status="active",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(recipient)
        db.commit()
    finally:
        db.close()


def count_odds_and_alerts():
    db = SessionLocal()
    try:
        return db.query(OddsSnapshot).count(), db.query(Alert).count()
    finally:
        db.close()


def test_sync_telegram_recipients_detects_private_chat(monkeypatch):
    from app.services import telegram_notifier

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(
        telegram_notifier.httpx,
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


def test_telegram_auto_sync_service_skips_without_token(monkeypatch):
    from app.services.telegram_notifier import sync_telegram_recipients_from_telegram

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")

    db = SessionLocal()
    try:
        result = sync_telegram_recipients_from_telegram(db)
    finally:
        db.close()

    assert result["status"] == "skipped"
    assert result["error"] == "telegram_not_configured"


def test_telegram_auto_sync_service_upserts_without_duplicates(monkeypatch):
    from app.services import telegram_notifier
    from app.services.telegram_notifier import sync_telegram_recipients_from_telegram

    deactivate_telegram_recipients()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(
        telegram_notifier.httpx,
        "get",
        lambda *args, **kwargs: FakeTelegramResponse(),
    )
    counts_before = count_odds_and_alerts()

    db = SessionLocal()
    try:
        first_result = sync_telegram_recipients_from_telegram(db)
        second_result = sync_telegram_recipients_from_telegram(db)
        recipients_count = (
            db.query(NotificationRecipient)
            .filter(
                NotificationRecipient.channel == "telegram",
                NotificationRecipient.recipient_value == "987654321",
            )
            .count()
        )
    finally:
        db.close()
    counts_after = count_odds_and_alerts()

    assert first_result["status"] == "completed"
    assert second_result["status"] == "completed"
    assert first_result["synced_count"] == 1
    assert second_result["synced_count"] == 1
    assert recipients_count == 1
    assert counts_after == counts_before


def test_telegram_auto_sync_background_helper_can_run_with_mock(monkeypatch):
    from app import main as app_main
    from app.services import telegram_notifier

    deactivate_telegram_recipients()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(
        telegram_notifier.httpx,
        "get",
        lambda *args, **kwargs: FakeTelegramResponse(),
    )

    result = app_main.run_telegram_auto_sync_once()

    assert result["status"] == "completed"
    assert result["synced_count"] == 1


def test_provider_competitions_auto_refresh_default_disabled(monkeypatch):
    from app import main as app_main

    monkeypatch.delenv("PROVIDER_COMPETITIONS_AUTO_REFRESH_ENABLED", raising=False)

    assert app_main.is_provider_competitions_auto_refresh_enabled() is False


def test_provider_competitions_auto_refresh_skips_without_api_key(monkeypatch):
    from app import main as app_main

    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_IO_KEY", raising=False)

    result = app_main.run_provider_competitions_auto_refresh_once()

    assert result["status"] == "skipped"
    assert result["error"] == "provider_auth_error"


def test_provider_competitions_auto_refresh_does_not_run_odds_ingestion(monkeypatch):
    from app import main as app_main

    counts_before = count_odds_and_alerts()

    monkeypatch.setattr(
        app_main,
        "refresh_provider_competitions_from_provider",
        lambda db, limit: {
            "provider": "odds_api_io",
            "events_received": 0,
            "competitions_found": 0,
            "competitions_upserted": 0,
            "competitions": [],
        },
    )

    result = app_main.run_provider_competitions_auto_refresh_once()
    counts_after = count_odds_and_alerts()

    assert result["competitions_upserted"] == 0
    assert counts_after == counts_before


def test_telegram_test_message_requires_bot_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")

    with TestClient(app) as client:
        response = client.post("/configuration/telegram-test-message")

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "telegram_not_configured"


def test_telegram_test_message_requires_active_recipients(monkeypatch):
    deactivate_telegram_recipients()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")

    with TestClient(app) as client:
        response = client.post("/configuration/telegram-test-message")

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "telegram_no_active_recipients"


def test_telegram_test_message_sends_to_active_recipient(monkeypatch):
    from app.services import telegram_notifier

    deactivate_telegram_recipients()
    create_active_telegram_recipient("987654321")
    FakeTelegramClient.sent_payloads = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(telegram_notifier.httpx, "Client", FakeTelegramClient)
    counts_before = count_odds_and_alerts()

    with TestClient(app) as client:
        response = client.post("/configuration/telegram-test-message")

    counts_after = count_odds_and_alerts()

    assert response.status_code == 200
    data = response.json()
    assert data["sent"] == 1
    assert data["failed"] == 0
    assert data["recipients_count"] == 1
    assert counts_after == counts_before
    assert len(FakeTelegramClient.sent_payloads) == 1
    assert FakeTelegramClient.sent_payloads[0]["json"]["chat_id"] == "987654321"
    assert (
        FakeTelegramClient.sent_payloads[0]["json"]["text"]
        == "OddSignal - test notifiche Telegram. Se ricevi questo messaggio, il bot online è configurato correttamente."
    )


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
    from app.services import telegram_notifier

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setattr(
        telegram_notifier.httpx,
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


def test_update_competition_provider_mapping_updates_existing_competition():
    competition_name = "Manual Mapping League " + uuid4().hex
    provider_slug = "manual-mapping-league-" + uuid4().hex

    with TestClient(app) as client:
        create_response = client.post(
            "/configuration/monitored-competitions",
            json={
                "competition_name": competition_name,
                "country": "Unknown",
                "provider": "odds_api_io",
                "provider_league_slug": None,
                "is_active": False,
            },
        )
        assert create_response.status_code == 200

        response = client.put(
            "/configuration/competitions/provider-mapping",
            json={
                "competition_name": competition_name,
                "country": "Test Country",
                "provider_league_slug": provider_slug,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == competition_name
        assert data["provider_league_slug"] == provider_slug
        assert data["is_monitored"] is True
        assert data["is_active"] is False

        available_response = client.get("/configuration/available-competitions")
        assert available_response.status_code == 200
        available = available_response.json()
        mapped = [item for item in available if item["name"] == competition_name]
        assert mapped
        assert mapped[0]["provider_league_slug"] == provider_slug


def test_update_competition_provider_mapping_rejects_empty_slug():
    with TestClient(app) as client:
        response = client.put(
            "/configuration/competitions/provider-mapping",
            json={
                "competition_name": "Missing Slug League",
                "provider_league_slug": "",
            },
        )

    assert response.status_code == 400
    assert "slug" in response.json()["detail"].lower()


class FakeProviderLeaguesRefresh:
    sport = "football"

    def get_leagues(self):
        return [
            {
                "name": "England - Premier League",
                "slug": "england-premier-league",
                "eventsCount": 12,
            },
            {
                "name": "Italy - Serie A",
                "slug": "italy-serie-a",
                "eventsCount": 8,
            },
        ]


def test_refresh_provider_leagues_upserts_competitions(monkeypatch):
    from app.routers import configuration

    monkeypatch.setattr(
        configuration,
        "OddsApiIoProvider",
        lambda **kwargs: FakeProviderLeaguesRefresh(),
    )

    with TestClient(app) as client:
        response = client.post("/configuration/provider-leagues/refresh")

    assert response.status_code == 200
    data = response.json()

    assert data["leagues_received"] == 2
    assert data["leagues_upserted"] == 2

    with TestClient(app) as client:
        available_response = client.get("/configuration/available-competitions")

    available = available_response.json()
    premier = [
        item
        for item in available
        if item["name"] == "England - Premier League"
    ][0]
    serie_a = [
        item
        for item in available
        if item["name"] == "Italy - Serie A"
    ][0]

    assert premier["country"] == "England"
    assert premier["provider_league_slug"] == "england-premier-league"
    assert serie_a["country"] == "Italy"
    assert serie_a["provider_league_slug"] == "italy-serie-a"


def test_scheduler_activation_rejects_configuration_above_provider_plan_limit():
    with TestClient(app) as client:
        plan_response = client.put(
            "/configuration/provider-plan-settings",
            json={
                "plan_name": "Free Test",
                "hourly_request_limit": 1,
                "max_bookmakers": 2,
            },
        )
        assert plan_response.status_code == 200

        response = client.put(
            "/configuration/scheduler-settings",
            json={
                "enabled": True,
                "poll_interval_seconds": 300,
                "event_limit": 1,
            },
        )

    assert response.status_code == 400
    assert "troppo aggressiva" in response.json()["detail"]


def test_scheduler_activation_allows_unlimited_provider_plan():
    with TestClient(app) as client:
        plan_response = client.put(
            "/configuration/provider-plan-settings",
            json={
                "plan_name": "Illimitato Test",
                "hourly_request_limit": None,
                "max_bookmakers": 100,
            },
        )
        assert plan_response.status_code == 200

        response = client.put(
            "/configuration/scheduler-settings",
            json={
                "enabled": True,
                "poll_interval_seconds": 30,
                "event_limit": 10,
            },
        )

    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_get_provider_bookmaker_settings_returns_configured_bookmakers():
    with TestClient(app) as client:
        response = client.get("/configuration/provider-bookmaker-settings")

    assert response.status_code == 200
    data = response.json()

    assert data["bookmaker_count"] >= 1
    assert isinstance(data["bookmakers"], list)
    assert data["max_bookmakers"] >= 1
    assert "bookmakers_csv" in data


def test_update_provider_bookmaker_settings_normalizes_duplicates():
    with TestClient(app) as client:
        plan_response = client.put(
            "/configuration/provider-plan-settings",
            json={
                "plan_name": "Pro",
                "hourly_request_limit": 5000,
                "max_bookmakers": 15,
            },
        )
        assert plan_response.status_code == 200

        response = client.put(
            "/configuration/provider-bookmaker-settings",
            json={
                "bookmakers_csv": "Stake, Sbobet, stake,  Sbobet",
            },
        )

    assert response.status_code == 200
    data = response.json()

    assert data["bookmakers_csv"] == "Stake,Sbobet"
    assert data["bookmakers"] == ["Stake", "Sbobet"]
    assert data["bookmaker_count"] == 2


def test_update_provider_bookmaker_settings_rejects_above_plan_limit():
    with TestClient(app) as client:
        plan_response = client.put(
            "/configuration/provider-plan-settings",
            json={
                "plan_name": "Free Plan",
                "hourly_request_limit": 100,
                "max_bookmakers": 2,
            },
        )
        assert plan_response.status_code == 200

        response = client.put(
            "/configuration/provider-bookmaker-settings",
            json={
                "bookmakers_csv": "Stake,Sbobet,Bet365",
            },
        )

    assert response.status_code == 400
    assert "Troppi bookmaker" in response.json()["detail"]


def test_scheduler_activation_rejects_bookmakers_above_provider_plan_limit():
    with TestClient(app) as client:
        pro_plan_response = client.put(
            "/configuration/provider-plan-settings",
            json={
                "plan_name": "Pro",
                "hourly_request_limit": 5000,
                "max_bookmakers": 15,
            },
        )
        assert pro_plan_response.status_code == 200

        bookmakers_response = client.put(
            "/configuration/provider-bookmaker-settings",
            json={
                "bookmakers_csv": "Stake,Sbobet,Bet365",
            },
        )
        assert bookmakers_response.status_code == 200
        assert bookmakers_response.json()["bookmaker_count"] == 3

        free_plan_response = client.put(
            "/configuration/provider-plan-settings",
            json={
                "plan_name": "Free Plan",
                "hourly_request_limit": 100000,
                "max_bookmakers": 2,
            },
        )
        assert free_plan_response.status_code == 200

        scheduler_response = client.put(
            "/configuration/scheduler-settings",
            json={
                "enabled": True,
                "poll_interval_seconds": 300,
                "event_limit": 1,
            },
        )

    assert scheduler_response.status_code == 400
    assert "Configurazione bookmaker non compatibile" in scheduler_response.json()["detail"]
