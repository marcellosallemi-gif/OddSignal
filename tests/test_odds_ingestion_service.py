from app.services.odds_ingestion_service import _expand_market_aliases
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from datetime import datetime

from app.models import Alert, MonitoredCompetition, MonitoredMarket, OddsSnapshot
from app.services import odds_ingestion_service


EXPECTED_IGNORED_ODDS_BREAKDOWN_KEYS = {
    "inactive_competition",
    "missing_provider_league_slug",
    "inactive_market",
    "unsupported_market",
    "inactive_bookmaker",
    "missing_previous_snapshot",
    "unchanged_odds",
    "invalid_odds",
    "missing_event_mapping",
    "below_alert_threshold",
    "outside_alert_range",
    "other",
}

EXPECTED_IGNORED_EVENTS_BREAKDOWN_KEYS = {
    "inactive_competition",
    "missing_provider_league_slug",
    "other",
}




def add_monitored_competition(db, competition_name="Test League"):
    item = MonitoredCompetition(
        competition_name=competition_name,
        country="Test",
        provider="odds_api_io",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(item)
    db.commit()
    return item


def add_monitored_market(db, market_name="ML", is_active=True):
    item = MonitoredMarket(
        market_name=market_name,
        is_active=is_active,
        created_at=datetime.utcnow(),
    )
    db.add(item)
    db.commit()
    return item


def make_test_db(tmp_path):
    database_url = "sqlite:///" + str(tmp_path / "test_ingestion.db")
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    return TestingSessionLocal()


class FakeProvider:
    odds_decimal = 1.80

    def get_sample(self, limit=3, league_slugs=None):
        return {
            "provider": "odds_api_io",
            "sport": "football",
            "bookmakers": ["Stake"],
            "events_count": 1,
            "odds_count": 1,
            "events": [
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-1",
                    "sport": "football",
                    "sport_name": "Football",
                    "league_name": "Test League",
                    "league_slug": "test-league",
                    "home_team": "Home FC",
                    "away_team": "Away FC",
                    "event_date": "2026-08-01T20:00:00Z",
                    "status": "pending",
                    "raw": {},
                }
            ],
            "odds": [
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-1",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": "ML",
                    "selection": "home",
                    "line": None,
                    "odds_decimal": self.odds_decimal,
                    "updated_at": "2026-08-01T10:00:00Z",
                    "raw": {},
                }
            ],
        }


def test_ingestion_inserts_first_snapshot_without_alert(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        FakeProvider.odds_decimal = 1.80
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProvider(),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["snapshots_inserted"] == 1
        assert result["alerts_created"] == 0
        assert "ignored_odds_breakdown" in result
        assert "ignored_market_breakdown_by_name" in result
        assert set(result["ignored_odds_breakdown"]) == EXPECTED_IGNORED_ODDS_BREAKDOWN_KEYS
        assert set(result["ignored_events_breakdown"]) == EXPECTED_IGNORED_EVENTS_BREAKDOWN_KEYS
        assert result["ignored_odds_breakdown"]["missing_previous_snapshot"] == 1
        assert db.query(OddsSnapshot).count() == 1
        assert db.query(Alert).count() == 0
    finally:
        db.close()


def test_ingestion_creates_standard_alert_on_eligible_variation(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProvider(),
        )

        FakeProvider.odds_decimal = 1.80
        odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        FakeProvider.odds_decimal = 1.98
        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        alert = db.query(Alert).first()

        assert result["snapshots_inserted"] == 1
        assert result["alerts_created"] == 1
        assert result["duplicate_alerts_skipped"] == 0
        assert alert is not None
        assert alert.alert_type == "standard_alert"
        assert alert.variation_percent == 10.0
        assert alert.direction == "increase"
    finally:
        db.close()


def test_ingestion_skips_recent_duplicate_alert(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        monkeypatch.setenv("ALERT_DEDUPLICATION_MINUTES", "30")
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProvider(),
        )

        FakeProvider.odds_decimal = 1.80
        odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        FakeProvider.odds_decimal = 1.98
        first_alert_result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        FakeProvider.odds_decimal = 2.18
        duplicate_result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert first_alert_result["alerts_created"] == 1
        assert duplicate_result["alerts_created"] == 0
        assert duplicate_result["duplicate_alerts_skipped"] == 1
        assert db.query(Alert).count() == 1
    finally:
        db.close()


class FakeProviderWithIgnoredMarket:
    def get_sample(self, limit=3, league_slugs=None):
        return {
            "provider": "odds_api_io",
            "sport": "football",
            "bookmakers": ["Stake"],
            "events_count": 1,
            "odds_count": 2,
            "events": [
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-ignored",
                    "sport": "football",
                    "sport_name": "Football",
                    "league_name": "Test League",
                    "league_slug": "test-league",
                    "home_team": "Home FC",
                    "away_team": "Away FC",
                    "event_date": "2026-08-01T20:00:00Z",
                    "status": "pending",
                    "raw": {},
                }
            ],
            "odds": [
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-ignored",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": "ML",
                    "selection": "home",
                    "line": None,
                    "odds_decimal": 1.80,
                    "updated_at": "2026-08-01T10:00:00Z",
                    "raw": {},
                },
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-ignored",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": "Team Total Home",
                    "selection": "over",
                    "line": 0.5,
                    "odds_decimal": 1.50,
                    "updated_at": "2026-08-01T10:00:00Z",
                    "raw": {},
                },
            ],
        }


def test_ingestion_ignores_non_mvp_markets(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProviderWithIgnoredMarket(),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 2
        assert result["odds_ignored"] == 1
        assert result["ignored_odds_breakdown"]["unsupported_market"] == 1
        assert result["ignored_market_breakdown_by_name"]["unsupported_market"]
        assert result["snapshots_inserted"] == 1
        assert db.query(OddsSnapshot).count() == 1

        snapshot = db.query(OddsSnapshot).first()
        assert snapshot.market == "ML"
    finally:
        db.close()


def test_ingestion_ignores_inactive_monitored_market(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "ML", is_active=False)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProvider(),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 1
        assert result["odds_ignored"] == 1
        assert result["ignored_odds_breakdown"]["inactive_market"] == 1
        assert result["ignored_market_breakdown_by_name"]["inactive_market"]
        assert result["snapshots_inserted"] == 0
        assert db.query(OddsSnapshot).count() == 0
    finally:
        db.close()


def test_ingestion_accepts_active_monitored_market(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "ML", is_active=True)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProvider(),
        )

        FakeProvider.odds_decimal = 1.80
        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 1
        assert result["odds_ignored"] == 0
        assert result["snapshots_inserted"] == 1
        assert db.query(OddsSnapshot).count() == 1
    finally:
        db.close()


def test_ingestion_ignores_unmonitored_competitions(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProvider(),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["active_competitions_count"] == 0
        assert result["events_received"] == 1
        assert result["events_ignored"] == 1
        assert result["ignored_events_breakdown"]["inactive_competition"] == 1
        assert result["odds_ignored"] == 1
        assert result["ignored_odds_breakdown"]["missing_event_mapping"] == 1
        assert result["snapshots_inserted"] == 0
        assert db.query(OddsSnapshot).count() == 0
    finally:
        db.close()


def test_parse_datetime_handles_provider_fractional_timezone_format():
    from app.services.odds_ingestion_service import _expand_market_aliases, _parse_datetime

    parsed = _parse_datetime("2026-05-19T09:35:23.33+00:00")

    assert parsed is not None


def test_ingestion_notifies_only_odds_decreases(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)
    captured_notifications = []

    def fake_send_telegram_alert_summary(db, alerts):
        captured_notifications.append([alert.direction for alert in alerts])
        return {"logs_created": len(alerts)}

    try:
        add_monitored_competition(db)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProvider(),
        )
        monkeypatch.setattr(
            odds_ingestion_service,
            "send_telegram_alert_summary",
            fake_send_telegram_alert_summary,
        )

        FakeProvider.odds_decimal = 1.80
        odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        FakeProvider.odds_decimal = 1.98
        increase_result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        FakeProvider.odds_decimal = 1.60
        decrease_result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert increase_result["alerts_created"] == 1
        assert increase_result["notification_logs_created"] == 0

        assert decrease_result["alerts_created"] == 1
        assert decrease_result["notification_logs_created"] == 1

        assert captured_notifications == [["decrease"]]

        alerts = db.query(Alert).order_by(Alert.id).all()
        assert alerts[0].direction == "increase"
        assert alerts[1].direction == "decrease"
        assert alerts[1].alert_type == "critical_alert"
    finally:
        db.close()



def test_market_aliases_expand_dashboard_names_to_provider_names():
    assert "ML" in _expand_market_aliases({"1X2"})
    assert "Totals" in _expand_market_aliases({"Over/Under 2.5"})
    assert "Both Teams To Score" in _expand_market_aliases({"Goal/No Goal"})
    assert "Spread" in _expand_market_aliases({"Handicap principale"})
    assert "Double Chance" in _expand_market_aliases({"Doppia chance"})
