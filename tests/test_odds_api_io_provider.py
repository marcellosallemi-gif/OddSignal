from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.odds_api_io_provider import OddsApiIoProvider


TEST_API_KEY = "test_dummy_key_123456789"


def parse_query(url):
    return parse_qs(urlparse(url).query)


def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.delenv("ODDS_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ODDS_API_KEY is missing"):
        OddsApiIoProvider()


def test_placeholder_api_key_raises_clear_error(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.setenv("ODDS_API_KEY", "PASTE_YOUR_API_KEY_HERE")

    with pytest.raises(RuntimeError, match="ODDS_API_KEY is missing"):
        OddsApiIoProvider()


def test_build_bookmakers_url_ends_with_bookmakers(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.setenv("ODDS_API_KEY", TEST_API_KEY)

    url = OddsApiIoProvider().build_bookmakers_url()

    assert url.endswith("/bookmakers")


def test_build_events_url_contains_football_sport(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.setenv("ODDS_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("ODDS_API_SPORT", "football")

    query = parse_query(OddsApiIoProvider().build_events_url())

    assert query["sport"] == ["football"]


def test_build_events_url_contains_pending_status(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.setenv("ODDS_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("ODDS_API_STATUS", "pending")

    query = parse_query(OddsApiIoProvider().build_events_url())

    assert query["status"] == ["pending"]


def test_build_events_url_contains_limit(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.setenv("ODDS_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("ODDS_API_EVENT_LIMIT", "10")

    query = parse_query(OddsApiIoProvider().build_events_url())

    assert query["limit"] == ["10"]


def test_build_event_odds_url_contains_event_id(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.setenv("ODDS_API_KEY", TEST_API_KEY)

    query = parse_query(OddsApiIoProvider().build_event_odds_url("event-123"))

    assert query["eventId"] == ["event-123"]


def test_build_event_odds_url_contains_bookmakers(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.setenv("ODDS_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("ODDS_API_BOOKMAKERS", "Stake,Sbobet")

    query = parse_query(OddsApiIoProvider().build_event_odds_url("event-123"))

    assert query["bookmakers"] == ["Stake,Sbobet"]


def test_build_multi_odds_url_contains_event_ids(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.setenv("ODDS_API_KEY", TEST_API_KEY)

    query = parse_query(OddsApiIoProvider().build_multi_odds_url(["event-1", 2]))

    assert query["eventIds"] == ["event-1,2"]


def test_masked_api_key_never_returns_full_key(monkeypatch):
    monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
    monkeypatch.setenv("ODDS_API_KEY", TEST_API_KEY)

    provider = OddsApiIoProvider()

    assert provider.masked_api_key() != TEST_API_KEY
    assert TEST_API_KEY not in provider.masked_api_key()


def test_provider_blocks_request_when_rate_limit_cooldown_is_active(monkeypatch, tmp_path):
    from datetime import datetime, timedelta, timezone

    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models import Base, ProviderApiRateLimitState, ProviderPlanSetting
    from app.services.odds_api_io_provider import OddsApiIoProvider

    engine = create_engine(
        "sqlite:///" + str(tmp_path / "cooldown.db"),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    class ClientShouldNotBeCalled:
        def __init__(self, *args, **kwargs):
            raise AssertionError("HTTP client should not be called during cooldown.")

    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        db.add(
            ProviderPlanSetting(
                plan_name="Free Plan",
                hourly_request_limit=100,
                max_bookmakers=2,
                created_at=now,
            )
        )
        db.add(
            ProviderApiRateLimitState(
                provider="odds_api_io",
                blocked_until=now + timedelta(minutes=30),
                reason="test cooldown",
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

        monkeypatch.setenv("ODDS_API_SKIP_DOTENV", "1")
        monkeypatch.setenv("ODDS_API_KEY", "test-key")
        monkeypatch.setattr(httpx, "Client", ClientShouldNotBeCalled)

        provider = OddsApiIoProvider(bookmakers_csv="Stake,Sbobet", usage_db=db)

        try:
            provider.get_events(limit=1, bookmaker="Stake")
        except RuntimeError as exc:
            assert "cooldown active" in str(exc)
        else:
            raise AssertionError("Expected provider cooldown to block request.")
    finally:
        db.close()



def test_classify_provider_error_handles_local_cooldown():
    from app.services.odds_api_io_provider import classify_provider_error

    status_code, detail = classify_provider_error(
        RuntimeError(
            "Provider API cooldown active until 2026-05-20 10:41:17. "
            "Endpoint blocked before calling Odds-API.io: /events."
        )
    )

    assert status_code == 429
    assert detail["error"] == "provider_rate_limit_cooldown"
    assert "cooldown locale" in detail["message"]


def test_classify_provider_error_handles_local_hourly_limit():
    from app.services.odds_api_io_provider import classify_provider_error

    status_code, detail = classify_provider_error(
        RuntimeError(
            "Provider API local hourly limit reached: 100/100 requests used. "
            "Endpoint blocked before calling Odds-API.io: /events."
        )
    )

    assert status_code == 429
    assert detail["error"] == "provider_local_rate_limit"
    assert "Limite locale" in detail["message"]


def test_manual_odds_check_response_contains_executed_at(monkeypatch):
    from app.routers import odds_provider

    monkeypatch.setattr(
        odds_provider,
        "ingest_odds_sample",
        lambda db, limit: {
            "status": "completed",
            "limit": limit,
            "ignored_odds_breakdown": {
                "inactive_market": 0,
                "missing_event_mapping": 0,
            },
            "ignored_events_breakdown": {
                "inactive_competition": 0,
            },
        },
    )

    with TestClient(app) as client:
        response = client.post("/api/odds-provider/ingest-sample?limit=1")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["executed_at"], str)
    assert data["executed_at"]
    assert datetime.fromisoformat(data["executed_at"]).tzinfo is not None
    assert "ignored_odds_breakdown" in data
    assert "ignored_events_breakdown" in data
