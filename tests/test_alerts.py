from datetime import datetime

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Alert, Event, NotificationLog
from app.services.alert_repository import save_alert


def clear_alerts():
    db = SessionLocal()
    try:
        db.query(NotificationLog).delete()
        db.query(Alert).delete()
        db.commit()
    finally:
        db.close()


def test_get_alerts_returns_empty_list_without_alerts():
    with TestClient(app) as client:
        clear_alerts()
        response = client.get("/alerts")

    assert response.status_code == 200
    assert response.json() == []


def test_get_alerts_returns_readable_alert_fields():
    with TestClient(app) as client:
        clear_alerts()
        db = SessionLocal()
        try:
            event = db.query(Event).order_by(Event.id).first()
            save_alert(
                db,
                {
                    "event_id": event.id,
                    "provider": "MockProvider A",
                    "bookmaker": "MockBook A",
                    "market": "Over/Under 2.5",
                    "selection": "Over 2.5",
                    "previous_odds": 1.80,
                    "current_odds": 2.00,
                    "variation_percent": 11.11,
                    "direction": "increase",
                    "alert_type": "standard_alert",
                    "created_at": datetime(2026, 5, 17, 10, 0),
                },
            )
        finally:
            db.close()

        response = client.get("/alerts")

    assert response.status_code == 200

    alerts = response.json()
    assert len(alerts) == 1

    alert = alerts[0]
    assert "event" in alert
    assert "sport" in alert
    assert "country" in alert
    assert "category" in alert
    assert "competition" in alert
    assert "event_start_time" in alert
    assert "provider" in alert
    assert "bookmaker" in alert
    assert "market" in alert
    assert "selection" in alert
    assert "previous_odds" in alert
    assert "current_odds" in alert
    assert "variation_percent" in alert
    assert "direction" in alert
    assert "alert_type" in alert
    assert "created_at" in alert
    assert alert["sport"] in {"football", "n/d"}
    assert alert["country"]
    assert alert["category"]

    clear_alerts()


def test_delete_recent_alerts_removes_all_alert_rows():
    with TestClient(app) as client:
        clear_alerts()
        db = SessionLocal()
        try:
            events_count = db.query(Event).count()
            event = db.query(Event).order_by(Event.id).first()
            for selection, created_at in [
                ("Over 2.5", datetime(2026, 5, 17, 10, 0)),
                ("Under 2.5", datetime(2026, 5, 17, 11, 0)),
            ]:
                save_alert(
                    db,
                    {
                        "event_id": event.id,
                        "provider": "MockProvider A",
                        "bookmaker": "MockBook A",
                        "market": "Over/Under 2.5",
                        "selection": selection,
                        "previous_odds": 1.80,
                        "current_odds": 2.00,
                        "variation_percent": 11.11,
                        "direction": "increase",
                        "alert_type": "standard_alert",
                        "created_at": created_at,
                    },
                )
        finally:
            db.close()

        response = client.delete("/alerts/recent?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["deleted_count"] == 2
    assert payload["message"] == "Alert cancellati."

    db = SessionLocal()
    try:
        assert db.query(Alert).count() == 0
        assert db.query(Event).count() == events_count
    finally:
        db.close()
        clear_alerts()


def test_delete_recent_alerts_removes_linked_notification_logs_first():
    with TestClient(app) as client:
        clear_alerts()
        db = SessionLocal()
        try:
            event = db.query(Event).order_by(Event.id).first()
            alert = save_alert(
                db,
                {
                    "event_id": event.id,
                    "provider": "MockProvider A",
                    "bookmaker": "MockBook A",
                    "market": "Over/Under 2.5",
                    "selection": "Over 2.5",
                    "previous_odds": 1.80,
                    "current_odds": 2.00,
                    "variation_percent": 11.11,
                    "direction": "increase",
                    "alert_type": "standard_alert",
                    "created_at": datetime(2026, 5, 17, 10, 0),
                },
            )
            db.add(
                NotificationLog(
                    alert_id=alert.id,
                    event_id=event.id,
                    channel="telegram",
                    status="sent",
                    recipient="123",
                    message="test",
                    sent_at=datetime(2026, 5, 17, 10, 1),
                )
            )
            db.commit()
        finally:
            db.close()

        response = client.delete("/alerts/recent?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["deleted_count"] == 1
    assert payload["deleted_notification_logs"] == 1

    db = SessionLocal()
    try:
        assert db.query(Alert).count() == 0
        assert db.query(NotificationLog).count() == 0
    finally:
        db.close()
        clear_alerts()



def test_delete_recent_alerts_endpoint_returns_deleted_count():
    with TestClient(app) as client:
        response = client.delete("/alerts/recent")

    assert response.status_code == 200
    payload = response.json()
    assert "deleted_count" in payload
    assert "deleted_notification_logs" in payload
