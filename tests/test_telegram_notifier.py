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
    TELEGRAM_SAFE_MESSAGE_LIMIT,
    build_alert_message,
    build_alerts_summary_messages,
    get_active_telegram_recipients,
    readable_selection_label,
    send_telegram_alert,
    send_telegram_alert_summary,
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


def create_many_alerts(db, count=50):
    first_alert = create_alert(db)
    alerts = [first_alert]

    for index in range(2, count + 1):
        alert = Alert(
            event_id=first_alert.event_id,
            provider="odds_api_io",
            bookmaker="Stake" if index % 2 else "Sbobet",
            market="ML",
            selection=f"selection-{index}",
            previous_odds=2.00,
            current_odds=1.70,
            variation_percent=-15.0 - (index / 100),
            direction="decrease",
            alert_type="critical_alert",
            created_at=datetime.utcnow(),
        )
        db.add(alert)
        alerts.append(alert)

    db.commit()
    for alert in alerts:
        db.refresh(alert)

    return alerts


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

        assert "OddSignal - Alert quote" in message
        assert "Sport: Calcio" in message
        assert "Nazione: Italy" in message
        assert "Categoria: Serie A" in message
        assert "Data/Ora evento: 15/08/2026 18:30" in message
        assert "Inter vs Milan" in message
        assert "Serie A" in message
        assert "Stake" in message
        assert "1X2" in message
        assert "ML" not in message
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

        assert "OddSignal - Alert quote (parte 1/1)" in message
        assert "Alert totali generati: 3" in message
        assert "Alert in questa parte: 3" in message
        assert "Sport: Calcio" in message
        assert "Nazione: Italy" in message
        assert "Categoria: Serie A" in message
        assert "Data/Ora evento: 15/08/2026 18:30" in message
        assert "Stake" in message
        assert "Sbobet" in message
        assert "-16.28%" in message
        assert "-14.86%" in message
        assert "11.11%" in message
    finally:
        db.close()


def test_readable_market_label_maps_provider_markets_to_user_labels():
    from app.services.telegram_notifier import readable_market_label

    assert readable_market_label("ML") == "1X2"
    assert readable_market_label("Totals") == "Over/Under"
    assert readable_market_label("Totals 2.5") == "Over/Under 2.5"
    assert readable_market_label("Both Teams To Score") == "Goal/No Goal"
    assert readable_market_label("Spread -1.75") == "Handicap -1.75"
    assert readable_market_label("European Handicap -1") == "Handicap europeo -1"
    assert readable_market_label("Exact Score") == "Exact Score"


def test_readable_selection_label_formats_line_and_double_chance_description():
    assert readable_selection_label("ML", "home", "Inter", "Milan") == "1 - Inter"
    assert readable_selection_label("ML", "draw", "Inter", "Milan") == "X - Pareggio"
    assert readable_selection_label("ML", "away", "Inter", "Milan") == "2 - Milan"
    assert readable_selection_label("Totals 2.5", "Under") == "Under 2.5"
    assert readable_selection_label("Totals 2.5", "over") == "Over 2.5"
    assert readable_selection_label("Double Chance", "1X") == "1X - Casa o Pareggio"
    assert readable_selection_label("Double Chance", "X2") == "X2 - Pareggio o Trasferta"
    assert readable_selection_label("Double Chance", "12") == "12 - Casa o Trasferta"
    assert readable_selection_label("Double Chance", "1X", "Inter", "Milan") == "1X - Inter o Pareggio"
    assert readable_selection_label("Double Chance", "X2", "Inter", "Milan") == "X2 - Pareggio o Milan"
    assert readable_selection_label("Double Chance", "12", "Inter", "Milan") == "12 - Inter o Milan"
    assert readable_selection_label("Spread -1.5", "home", "Inter", "Milan") == "Inter handicap -1.5"


def test_build_alert_message_shows_readable_selection_and_line(tmp_path):
    db = make_test_db(tmp_path)

    try:
        alert = create_alert(db)
        alert.market = "Totals 2.5"
        alert.selection = "Under"
        db.commit()
        db.refresh(alert)

        message = build_alert_message(alert)

        assert "Mercato: Over/Under 2.5" in message
        assert "Selezione: Under 2.5" in message
        assert "Linea: 2.5" in message
    finally:
        db.close()


def test_build_alert_message_shows_double_chance_description(tmp_path):
    db = make_test_db(tmp_path)

    try:
        alert = create_alert(db)
        alert.market = "Double Chance"
        alert.selection = "1X"
        db.commit()
        db.refresh(alert)

        message = build_alert_message(alert)

        assert "Mercato: Double Chance" in message
        assert "Selezione: 1X - Inter o Pareggio" in message
        assert "Selezione: under" not in message
    finally:
        db.close()


def test_summary_alert_message_contains_type_provider_and_team_selection(tmp_path):
    db = make_test_db(tmp_path)

    try:
        alert = create_alert(db)
        alert.market = "Double Chance"
        alert.selection = "X2"
        db.commit()
        db.refresh(alert)

        messages = build_alerts_summary_messages([alert])

        assert "Selezione: X2 - Pareggio o Milan" in messages[0]
        assert "Tipo alert: standard_alert" in messages[0]
        assert "Provider: odds_api_io" in messages[0]
        assert "Sport: Calcio" in messages[0]
        assert "Nazione: Italy" in messages[0]
        assert "Categoria: Serie A" in messages[0]
    finally:
        db.close()


def test_build_alerts_summary_messages_splits_long_summary_under_safe_limit(tmp_path):
    db = make_test_db(tmp_path)

    try:
        alerts = create_many_alerts(db, count=50)

        messages = build_alerts_summary_messages(alerts)

        assert len(messages) > 1
        assert all(len(message) <= TELEGRAM_SAFE_MESSAGE_LIMIT for message in messages)
        assert "OddSignal - Alert quote (parte 1/" in messages[0]
        assert "Alert totali generati: 50" in messages[0]
    finally:
        db.close()


def test_build_alerts_summary_messages_truncates_single_long_alert_block(tmp_path):
    db = make_test_db(tmp_path)

    try:
        alert = create_alert(db)
        alert.selection = "very-long-selection-" + ("x" * 5000)
        db.commit()
        db.refresh(alert)

        messages = build_alerts_summary_messages([alert])

        assert len(messages) == 1
        assert len(messages[0]) <= TELEGRAM_SAFE_MESSAGE_LIMIT
        assert "…contenuto abbreviato" in messages[0]
    finally:
        db.close()


class FakeTelegramResponse:
    def __init__(self, status_code=200, text="OK"):
        self.status_code = status_code
        self.text = text


class FakeTelegramClient:
    posts = []
    responses = []

    def __init__(self, timeout=15.0):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def post(self, url, json):
        self.posts.append({"url": url, "json": json})
        if self.responses:
            return self.responses.pop(0)
        return FakeTelegramResponse()


def test_send_telegram_alert_summary_sends_all_parts_to_two_recipients(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        monkeypatch.setattr("app.services.telegram_notifier.httpx.Client", FakeTelegramClient)
        FakeTelegramClient.posts = []
        FakeTelegramClient.responses = []

        create_telegram_recipient(db, recipient_value="111")
        create_telegram_recipient(db, recipient_value="222")
        alerts = create_many_alerts(db, count=50)

        result = send_telegram_alert_summary(db=db, alerts=alerts)
        db.commit()

        assert result["recipients_count"] == 2
        assert result["parts_count"] > 1
        assert result["messages_attempted"] == result["parts_count"] * 2
        assert result["messages_sent"] == result["messages_attempted"]
        assert result["messages_failed"] == 0
        assert len(FakeTelegramClient.posts) == result["messages_attempted"]
        assert db.query(NotificationLog).count() == result["messages_attempted"]
        assert all(
            len(item["json"]["text"]) <= TELEGRAM_SAFE_MESSAGE_LIMIT
            for item in FakeTelegramClient.posts
        )
    finally:
        db.close()


def test_send_telegram_alert_summary_logs_part_failure_without_crashing(monkeypatch, tmp_path):
    db = make_test_db(tmp_path)

    try:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        monkeypatch.setattr("app.services.telegram_notifier.httpx.Client", FakeTelegramClient)
        FakeTelegramClient.posts = []
        FakeTelegramClient.responses = [
            FakeTelegramResponse(status_code=400, text="Bad Request: message is too long")
        ]

        create_telegram_recipient(db, recipient_value="111")
        alerts = create_many_alerts(db, count=50)

        result = send_telegram_alert_summary(db=db, alerts=alerts)
        db.commit()

        failed_log = (
            db.query(NotificationLog)
            .filter(NotificationLog.status == "failed")
            .first()
        )

        assert result["messages_attempted"] == result["parts_count"]
        assert result["messages_failed"] == 1
        assert result["messages_sent"] == result["messages_attempted"] - 1
        assert failed_log is not None
        assert "Bad Request: message is too long" in failed_log.error_message
    finally:
        db.close()
