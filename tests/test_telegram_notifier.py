from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Alert, Competition, Event, NotificationLog, Team
from app.services.telegram_notifier import build_alert_message, send_telegram_alert


def make_test_db(tmp_path):
    database_url = "sqlite:///" + str(tmp_path / "test_telegram.db")
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


def create_alert(db):
    competition = Competition(name="Serie A", country="Italy")
    home_team = Team(name="Inter")
    away_team = Team(name="Milan")

    db.add_all([competition, home_team, away_team])
    db.flush()

    event = Event(
        competition_id=competition.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        start_time=datetime(2026, 8, 15, 18, 30),
        status="scheduled",
    )

    db.add(event)
    db.flush()

    alert = Alert(
        event_id=event.id,
        provider="odds_api_io",
        bookmaker="Stake",
        market="ML",
        selection="home",
        previous_odds=1.80,
        current_odds=2.00,
        variation_percent=11.11,
        direction="increase",
        alert_type="standard_alert",
        created_at=datetime.utcnow(),
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return alert


def test_build_alert_message_contains_core_details(tmp_path):
    db = make_test_db(tmp_path)

    try:
        alert = create_alert(db)
        message = build_alert_message(alert)

        assert "Alert quote calcio" in message
        assert "Inter vs Milan" in message
        assert "Serie A" in message
        assert "Stake" in message
        assert "ML" in message
        assert "11.11%" in message
    finally:
        db.close()


def test_send_telegram_alert_skips_when_not_configured(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        alert = create_alert(db)
        result = send_telegram_alert(db=db, alert=alert)
        db.commit()

        log = db.query(NotificationLog).first()

        assert result["status"] == "skipped"
        assert log is not None
        assert log.status == "skipped"
        assert log.channel == "telegram"
        assert "Telegram is not configured" in log.error_message
    finally:
        db.close()
