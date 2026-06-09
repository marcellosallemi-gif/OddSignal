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
    "disabled_market",
    "unsupported_market",
    "unsupported_line",
    "inactive_bookmaker",
    "missing_previous_snapshot",
    "unchanged_odds",
    "invalid_odds",
    "invalid_market_selection",
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

EXPECTED_DIAGNOSTIC_RESULT_KEYS = {
    "changed_odds_count",
    "unchanged_odds_count",
    "max_positive_variation_percent",
    "max_negative_variation_percent",
    "below_alert_threshold_count",
    "within_alert_range_count",
    "above_critical_threshold_count",
    "top_movements",
}




def add_monitored_competition(db, competition_name="Test League", sport="football"):
    item = MonitoredCompetition(
        competition_name=competition_name,
        country="Test",
        sport=sport,
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


class FakeProviderWithDiagnosticMovements:
    odds_by_key = {
        "home": 1.80,
        "draw": 3.00,
        "away": 2.00,
        "over": 1.80,
    }

    def get_sample(self, limit=3, league_slugs=None):
        odds = [
            {
                "provider": "odds_api_io",
                "provider_event_id": "fake-event-diagnostics",
                "event": "Home FC vs Away FC",
                "league_name": "Test League",
                "bookmaker": "Stake",
                "market_name": "ML",
                "selection": "home",
                "line": None,
                "odds_decimal": self.odds_by_key["home"],
                "updated_at": "2026-08-01T10:00:00Z",
                "raw": {},
            },
            {
                "provider": "odds_api_io",
                "provider_event_id": "fake-event-diagnostics",
                "event": "Home FC vs Away FC",
                "league_name": "Test League",
                "bookmaker": "Stake",
                "market_name": "ML",
                "selection": "draw",
                "line": None,
                "odds_decimal": self.odds_by_key["draw"],
                "updated_at": "2026-08-01T10:00:00Z",
                "raw": {},
            },
            {
                "provider": "odds_api_io",
                "provider_event_id": "fake-event-diagnostics",
                "event": "Home FC vs Away FC",
                "league_name": "Test League",
                "bookmaker": "Stake",
                "market_name": "ML",
                "selection": "away",
                "line": None,
                "odds_decimal": self.odds_by_key["away"],
                "updated_at": "2026-08-01T10:00:00Z",
                "raw": {},
            },
            {
                "provider": "odds_api_io",
                "provider_event_id": "fake-event-diagnostics",
                "event": "Home FC vs Away FC",
                "league_name": "Test League",
                "bookmaker": "Stake",
                "market_name": "Totals",
                "selection": "over",
                "line": 2.5,
                "odds_decimal": self.odds_by_key["over"],
                "updated_at": "2026-08-01T10:00:00Z",
                "raw": {},
            },
        ]

        return {
            "provider": "odds_api_io",
            "sport": "football",
            "bookmakers": ["Stake"],
            "events_count": 1,
            "odds_count": len(odds),
            "events": [
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-diagnostics",
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
            "odds": odds,
        }


class FakeTennisProvider:
    odds_decimal = 1.80

    def get_sample(self, limit=3, league_slugs=None):
        return {
            "provider": "odds_api_io",
            "sport": "tennis",
            "bookmakers": ["Stake"],
            "events_count": 1,
            "odds_count": 1,
            "events": [
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-tennis-event-1",
                    "sport": "tennis",
                    "sport_name": "Tennis",
                    "league_name": "ATP Safe Test",
                    "league_slug": "atp-safe-test",
                    "home_team": "Sinner",
                    "away_team": "Alcaraz",
                    "event_date": "2026-08-01T20:00:00Z",
                    "status": "pending",
                    "raw": {},
                }
            ],
            "odds": [
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-tennis-event-1",
                    "event": "Sinner vs Alcaraz",
                    "league_name": "ATP Safe Test",
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


class FakeProviderWithTotalsLine:
    def __init__(self, line, odds_decimal=1.80):
        self.line = line
        self.odds_decimal = odds_decimal

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
                    "provider_event_id": "fake-event-totals-line",
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
                    "provider_event_id": "fake-event-totals-line",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": "Totals",
                    "selection": "over",
                    "line": self.line,
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
        assert "excluded_market_breakdown_by_name" in result
        assert EXPECTED_DIAGNOSTIC_RESULT_KEYS.issubset(result)
        assert EXPECTED_DIAGNOSTIC_RESULT_KEYS.issubset(result["sport_results"][0])
        assert set(result["ignored_odds_breakdown"]) == EXPECTED_IGNORED_ODDS_BREAKDOWN_KEYS
        assert set(result["ignored_events_breakdown"]) == EXPECTED_IGNORED_EVENTS_BREAKDOWN_KEYS
        assert result["odds_processed"] == 1
        assert result["odds_excluded"] == 0
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


def test_ingestion_returns_diagnostic_movements(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProviderWithDiagnosticMovements(),
        )

        FakeProviderWithDiagnosticMovements.odds_by_key = {
            "home": 1.80,
            "draw": 3.00,
            "away": 2.00,
            "over": 1.80,
        }
        odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        FakeProviderWithDiagnosticMovements.odds_by_key = {
            "home": 1.80,
            "draw": 3.15,
            "away": 2.20,
            "over": 2.10,
        }
        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        decisions = {
            item["selection"]: item["decision"]
            for item in result["top_movements"]
        }

        assert result["changed_odds_count"] == 3
        assert result["unchanged_odds_count"] == 1
        assert result["below_alert_threshold_count"] == 1
        assert result["within_alert_range_count"] == 1
        assert result["above_critical_threshold_count"] == 1
        assert result["max_positive_variation_percent"] == 16.67
        assert result["max_negative_variation_percent"] is None
        assert result["ignored_odds_breakdown"]["below_alert_threshold"] == 1
        assert len(result["top_movements"]) == 4
        assert len(
            [
                item
                for item in result["top_movements"]
                if item["decision"] == "below_threshold"
            ]
        ) == result["below_alert_threshold_count"]
        assert decisions["home"] == "unchanged"
        assert decisions["draw"] == "below_threshold"
        assert decisions["away"] == "alert_created"
        assert decisions["Over"] == "alert_created"
        assert result["top_movements"][0]["sport"] == "football"
        assert result["top_movements"][0]["competition"] == "Test League"
        assert result["top_movements"][0]["event"] == "Home FC vs Away FC"
        assert result["top_movements"][0]["bookmaker"] == "Stake"
        assert result["top_movements"][0]["provider"] == "odds_api_io"
    finally:
        db.close()


def test_tennis_ingestion_stores_safe_market_without_creating_alert(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(
            db,
            competition_name="ATP Safe Test",
            sport="tennis",
        )
        add_monitored_market(db, market_name="ML", is_active=True)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeTennisProvider(),
        )

        FakeTennisProvider.odds_decimal = 1.80
        odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        FakeTennisProvider.odds_decimal = 1.98
        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["sport"] == "tennis"
        assert result["snapshots_inserted"] == 1
        assert result["alerts_created"] == 0
        assert result["tennis_alerts_skipped"] == 1
        assert db.query(OddsSnapshot).count() == 2
        assert db.query(Alert).count() == 0
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
        assert duplicate_result["changed_odds_count"] == 1
        assert duplicate_result["within_alert_range_count"] == 1
        assert duplicate_result["top_movements"][0]["decision"] == "duplicate"
        assert db.query(Alert).count() == 1
    finally:
        db.close()


def test_ingestion_merges_diagnostics_for_multiple_sports(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_competition(
            db,
            competition_name="ATP Safe Test",
            sport="tennis",
        )
        add_monitored_market(db, market_name="ML", is_active=True)

        def fake_provider_factory(**kwargs):
            if kwargs.get("sport") == "tennis":
                return FakeTennisProvider()
            return FakeProvider()

        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            fake_provider_factory,
        )

        FakeProvider.odds_decimal = 1.80
        FakeTennisProvider.odds_decimal = 1.80
        odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        FakeProvider.odds_decimal = 1.98
        FakeTennisProvider.odds_decimal = 1.98
        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["sport"] == "multi"
        assert result["sports_processed"] == ["football", "tennis"]
        assert result["changed_odds_count"] == 2
        assert result["unchanged_odds_count"] == 0
        assert result["within_alert_range_count"] == 2
        assert result["alerts_created"] == 1
        assert result["tennis_alerts_skipped"] == 1
        assert result["max_positive_variation_percent"] == 10.0
        assert result["max_negative_variation_percent"] is None
        assert EXPECTED_DIAGNOSTIC_RESULT_KEYS.issubset(result)
        for sport_result in result["sport_results"]:
            assert EXPECTED_DIAGNOSTIC_RESULT_KEYS.issubset(sport_result)
        assert {item["sport"] for item in result["top_movements"]} == {
            "football",
            "tennis",
        }
        assert len(result["sport_results"]) == 2
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


class FakeProviderWithAdditionalMarkets:
    def get_sample(self, limit=3, league_slugs=None):
        return {
            "provider": "odds_api_io",
            "sport": "football",
            "bookmakers": ["Stake"],
            "events_count": 1,
            "odds_count": 3,
            "events": [
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-additional-markets",
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
                    "provider_event_id": "fake-event-additional-markets",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": "Double Chance",
                    "selection": "home_or_draw",
                    "line": None,
                    "odds_decimal": 1.35,
                    "updated_at": "2026-08-01T10:00:00Z",
                    "raw": {},
                },
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-additional-markets",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": "Draw No Bet",
                    "selection": "home",
                    "line": None,
                    "odds_decimal": 1.70,
                    "updated_at": "2026-08-01T10:00:00Z",
                    "raw": {},
                },
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-additional-markets",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": "European Handicap",
                    "selection": "home",
                    "line": -1,
                    "odds_decimal": 2.10,
                    "updated_at": "2026-08-01T10:00:00Z",
                    "raw": {},
                },
            ],
        }


class FakeProviderWithExcludedMarkets:
    def get_sample(self, limit=3, league_slugs=None):
        excluded_markets = [
            ("Spread HT", "home", 0.5),
            ("Totals HT", "over", 1.5),
            ("Corners Spread", "home", 1.5),
            ("Corners Totals", "over", 8.5),
            ("Bookings Totals", "over", 4.5),
            ("Team Total Home", "over", 1.5),
        ]

        odds = []
        for index, item in enumerate(excluded_markets):
            market_name, selection, line = item
            odds.append(
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-excluded-markets",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": market_name,
                    "selection": selection,
                    "line": line,
                    "odds_decimal": 1.50 + (index * 0.01),
                    "updated_at": "2026-08-01T10:00:00Z",
                    "raw": {},
                }
            )

        return {
            "provider": "odds_api_io",
            "sport": "football",
            "bookmakers": ["Stake"],
            "events_count": 1,
            "odds_count": len(odds),
            "events": [
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-excluded-markets",
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
            "odds": odds,
        }


class FakeProviderWithInvalidDoubleChanceSelection:
    odds_decimal = 1.80
    market_name = "Double Chance"
    selection = "under"
    line = None

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
                    "provider_event_id": "fake-event-invalid-double-chance",
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
                    "provider_event_id": "fake-event-invalid-double-chance",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": self.market_name,
                    "selection": self.selection,
                    "line": self.line,
                    "odds_decimal": self.odds_decimal,
                    "updated_at": "2026-08-01T10:00:00Z",
                    "raw": {},
                }
            ],
        }


class FakeProviderWithTotalsAndDoubleChanceSelections:
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
                    "provider_event_id": "fake-event-normalized-selections",
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
                    "provider_event_id": "fake-event-normalized-selections",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": "Double Chance",
                    "selection": "home_or_draw",
                    "line": None,
                    "odds_decimal": 1.35,
                    "updated_at": "2026-08-01T10:00:00Z",
                    "raw": {},
                },
                {
                    "provider": "odds_api_io",
                    "provider_event_id": "fake-event-normalized-selections",
                    "event": "Home FC vs Away FC",
                    "league_name": "Test League",
                    "bookmaker": "Stake",
                    "market_name": "Totals",
                    "selection": "under",
                    "line": 2.5,
                    "odds_decimal": 1.90,
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
        assert result["odds_processed"] == 1
        assert result["odds_excluded"] == 1
        assert result["ignored_odds_breakdown"]["unsupported_market"] == 1
        assert result["ignored_market_breakdown_by_name"]["unsupported_market"]["Team Total Home 0.5"] == 1
        assert result["excluded_market_breakdown_by_name"]["unsupported_market"]["Team Total Home 0.5"] == 1
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
        assert result["odds_processed"] == 0
        assert result["odds_excluded"] == 1
        assert result["ignored_odds_breakdown"]["inactive_market"] == 1
        assert result["ignored_market_breakdown_by_name"]["inactive_market"]["ML"] == 1
        assert result["excluded_market_breakdown_by_name"]["inactive_market"]["ML"] == 1
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


def test_ingestion_excludes_disabled_totals_line(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "Over/Under 0.5", is_active=False)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProviderWithTotalsLine(line=0.5),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 1
        assert result["odds_processed"] == 0
        assert result["snapshots_inserted"] == 0
        assert result["excluded_disabled_market"] == 1
        assert result["ignored_odds_breakdown"]["disabled_market"] == 1
        assert result["excluded_market_breakdown_by_name"]["disabled_market"]["Over/Under 0.5"] == 1
        assert db.query(OddsSnapshot).count() == 0
    finally:
        db.close()


def test_ingestion_processes_active_totals_line(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "Over/Under 2.5", is_active=True)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProviderWithTotalsLine(line=2.5),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 1
        assert result["odds_ignored"] == 0
        assert result["odds_processed"] == 1
        assert result["snapshots_inserted"] == 1
        assert db.query(OddsSnapshot).count() == 1
    finally:
        db.close()


def test_ingestion_excludes_unsupported_totals_line(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "Over/Under 2.5", is_active=True)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProviderWithTotalsLine(line=7.5),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 1
        assert result["odds_processed"] == 0
        assert result["snapshots_inserted"] == 0
        assert result["excluded_unsupported_line"] == 1
        assert result["ignored_odds_breakdown"]["unsupported_line"] == 1
        assert result["excluded_market_breakdown_by_name"]["unsupported_line"]["Over/Under 7.5"] == 1
        assert db.query(OddsSnapshot).count() == 0
    finally:
        db.close()


def test_ingestion_does_not_alert_for_disabled_totals_line(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)
    provider = FakeProviderWithTotalsLine(line=0.5, odds_decimal=1.80)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "Over/Under 0.5", is_active=False)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: provider,
        )

        odds_ingestion_service.ingest_odds_sample(db=db, limit=1)
        provider.odds_decimal = 1.98
        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["snapshots_inserted"] == 0
        assert result["alerts_created"] == 0
        assert db.query(OddsSnapshot).count() == 0
        assert db.query(Alert).count() == 0
    finally:
        db.close()


def test_ingestion_processes_added_supported_markets_when_active(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "Doppia chance", is_active=True)
        add_monitored_market(db, "Draw No Bet", is_active=True)
        add_monitored_market(db, "Handicap europeo", is_active=True)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProviderWithAdditionalMarkets(),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 3
        assert result["odds_ignored"] == 0
        assert result["odds_processed"] == 3
        assert result["odds_excluded"] == 0
        assert result["ignored_odds_breakdown"]["unsupported_market"] == 0
        assert result["snapshots_inserted"] == 3

        snapshot_markets = {snapshot.market for snapshot in db.query(OddsSnapshot).all()}
        assert snapshot_markets == {
            "Double Chance",
            "Draw No Bet",
            "European Handicap -1",
        }
    finally:
        db.close()


def test_ingestion_excludes_double_chance_with_under_selection(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "Double Chance", is_active=True)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProviderWithInvalidDoubleChanceSelection(),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 1
        assert result["odds_ignored"] == 1
        assert result["odds_excluded"] == 1
        assert result["ignored_odds_breakdown"]["invalid_market_selection"] == 1
        assert result["excluded_market_breakdown_by_name"]["invalid_market_selection"]["Double Chance"] == 1
        assert db.query(OddsSnapshot).count() == 0
        assert db.query(Alert).count() == 0
    finally:
        db.close()


def test_ingestion_excludes_active_unrecognized_market(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "Exact Score", is_active=True)

        provider = FakeProviderWithInvalidDoubleChanceSelection()
        provider.market_name = "Exact Score"
        provider.selection = "1-0"
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: provider,
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 1
        assert result["odds_ignored"] == 1
        assert result["ignored_odds_breakdown"]["unsupported_market"] == 1
        assert result["excluded_market_breakdown_by_name"]["unsupported_market"]["Exact Score"] == 1
        assert db.query(OddsSnapshot).count() == 0
    finally:
        db.close()


def test_ingestion_excludes_totals_without_line(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "Over/Under 2.5", is_active=True)

        provider = FakeProviderWithInvalidDoubleChanceSelection()
        provider.market_name = "Totals"
        provider.selection = "under"
        provider.line = None
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: provider,
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 1
        assert result["odds_ignored"] == 1
        assert result["ignored_odds_breakdown"]["invalid_market_selection"] == 1
        assert result["excluded_market_breakdown_by_name"]["invalid_market_selection"]["Totals"] == 1
        assert db.query(OddsSnapshot).count() == 0
    finally:
        db.close()


def test_ingestion_normalizes_supported_selections_and_requires_totals_line(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        add_monitored_market(db, "Double Chance", is_active=True)
        add_monitored_market(db, "Over/Under 2.5", is_active=True)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProviderWithTotalsAndDoubleChanceSelections(),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        snapshots = db.query(OddsSnapshot).order_by(OddsSnapshot.market).all()

        assert result["odds_received"] == 2
        assert result["odds_ignored"] == 0
        assert [(item.market, item.selection, item.line) for item in snapshots] == [
            ("Double Chance", "1X", None),
            ("Totals 2.5", "Under", 2.5),
        ]
    finally:
        db.close()


def test_ingestion_keeps_ht_corners_bookings_and_team_totals_excluded(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        add_monitored_competition(db)
        for market_name in [
            "Spread HT",
            "Totals HT",
            "Corner Handicap",
            "Corner Over/Under",
            "Cartellini Over/Under",
            "Team Total Home",
        ]:
            add_monitored_market(db, market_name, is_active=True)
        monkeypatch.setattr(
            odds_ingestion_service,
            "OddsApiIoProvider",
            lambda **kwargs: FakeProviderWithExcludedMarkets(),
        )

        result = odds_ingestion_service.ingest_odds_sample(db=db, limit=1)

        assert result["odds_received"] == 6
        assert result["odds_ignored"] == 6
        assert result["odds_processed"] == 0
        assert result["odds_excluded"] == 6
        assert result["ignored_odds_breakdown"]["unsupported_market"] == 6
        assert result["snapshots_inserted"] == 0
        assert db.query(OddsSnapshot).count() == 0

        ignored_names = result["ignored_market_breakdown_by_name"]["unsupported_market"]
        excluded_names = result["excluded_market_breakdown_by_name"]["unsupported_market"]
        for market_name in [
            "Spread HT 0.5",
            "Totals HT 1.5",
            "Corners Spread 1.5",
            "Corners Totals 8.5",
            "Bookings Totals 4.5",
            "Team Total Home 1.5",
        ]:
            assert ignored_names[market_name] == 1
            assert excluded_names[market_name] == 1
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
    assert "Totals 2.5" in _expand_market_aliases({"Over/Under 2.5"})
    assert "Both Teams To Score" in _expand_market_aliases({"Goal/No Goal"})
    assert "Spread" in _expand_market_aliases({"Handicap principale"})
    assert "Double Chance" in _expand_market_aliases({"Doppia chance"})
    assert "Double Chance" in _expand_market_aliases({"Double Chance"})
    assert "Draw No Bet" in _expand_market_aliases({"Draw No Bet"})
    assert "European Handicap" in _expand_market_aliases({"Handicap europeo"})
    assert "European Handicap" in _expand_market_aliases({"European Handicap"})
