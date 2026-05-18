from datetime import datetime

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Alert, Event
from app.services.alert_repository import save_alert


def clear_alerts():
    db = SessionLocal()
    try:
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
    assert "competition" in alert
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

    clear_alerts()
