from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Alert,
    Competition,
    Event,
    NotificationLog,
    NotificationRecipient,
    Team,
)
from app.services.telegram_notifier import (
    build_alert_message,
    get_active_telegram_recipients,
    send_telegram_alert,
)


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


def create_telegram_recipient(db, recipient_value="123456789", is_active=True):
    recipient = NotificationRecipient(
        channel="telegram",
        recipient_value=recipient_value,
        label="Test Telegram",
        is_active=is_active,
        created_at=datetime.utcnow(),
    )
    db.add(recipient)
    db.commit()
    db.refresh(recipient)
    return recipient


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


def test_get_active_telegram_recipients_reads_database(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        create_telegram_recipient(db, recipient_value="111")
        create_telegram_recipient(db, recipient_value="222", is_active=False)

        recipients = get_active_telegram_recipients(db)

        assert recipients == ["111"]
    finally:
        db.close()


def test_send_telegram_alert_skips_when_bot_token_missing(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        create_telegram_recipient(db)
        alert = create_alert(db)
        result = send_telegram_alert(db=db, alert=alert)
        db.commit()

        log = db.query(NotificationLog).first()

        assert result["status"] == "skipped"
        assert result["logs_created"] == 1
        assert log is not None
        assert log.status == "skipped"
        assert log.channel == "telegram"
        assert "Telegram bot token is not configured" in log.error_message
    finally:
        db.close()


def test_send_telegram_alert_skips_when_no_active_recipients(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        alert = create_alert(db)
        result = send_telegram_alert(db=db, alert=alert)
        db.commit()

        log = db.query(NotificationLog).first()

        assert result["status"] == "skipped"
        assert result["logs_created"] == 1
        assert log is not None
        assert log.status == "skipped"
        assert log.channel == "telegram"
        assert "No active Telegram recipients configured" in log.error_message
    finally:
        db.close()


def test_build_alerts_summary_message_contains_all_alerts(tmp_path):
    db = make_test_db(tmp_path)

    try:
        first_alert = create_alert(db)

        second_alert = Alert(
            event_id=first_alert.event_id,
            provider="odds_api_io",
            bookmaker="Sbobet",
            market="ML",
            selection="away",
            previous_odds=7.40,
            current_odds=6.30,
            variation_percent=-14.86,
            direction="decrease",
            alert_type="standard_alert",
            created_at=datetime.utcnow(),
        )

        third_alert = Alert(
            event_id=first_alert.event_id,
            provider="odds_api_io",
            bookmaker="Stake",
            market="ML",
            selection="away",
            previous_odds=8.60,
            current_odds=7.20,
            variation_percent=-16.28,
            direction="decrease",
            alert_type="critical_alert",
            created_at=datetime.utcnow(),
        )

        db.add_all([second_alert, third_alert])
        db.commit()
        db.refresh(first_alert)
        db.refresh(second_alert)
        db.refresh(third_alert)

        from app.services.telegram_notifier import build_alerts_summary_message

        message = build_alerts_summary_message(
            [first_alert, second_alert, third_alert]
        )

        assert "3 movimenti validi rilevati" in message
        assert "Critici: 1" in message
        assert "Standard: 2" in message
        assert "Stake" in message
        assert "Sbobet" in message
        assert "-16.28%" in message
        assert "-14.86%" in message
        assert "11.11%" in message
        assert "Apri la dashboard" not in message
    finally:
        db.close()
