import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Event, NotificationLog, OddsSnapshot
from app.services.telegram_notifier import is_telegram_configured


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    bookmakers = [
        bookmaker.strip()
        for bookmaker in os.getenv("ODDS_API_BOOKMAKERS", "").split(",")
        if bookmaker.strip()
    ]

    return {
        "provider": os.getenv("ODDS_PROVIDER", "unknown"),
        "sport": os.getenv("ODDS_API_SPORT", "unknown"),
        "bookmakers": bookmakers,
        "scheduler": {
            "enabled": os.getenv("ODDS_SCHEDULER_ENABLED", "0") == "1",
            "poll_interval_seconds": int(os.getenv("ODDS_POLL_INTERVAL_SECONDS", "300")),
            "event_limit": int(os.getenv("ODDS_SCHEDULER_EVENT_LIMIT", "1")),
        },
        "alerts": {
            "min_percent": float(os.getenv("ALERT_MIN_PERCENT", "8")),
            "max_percent": float(os.getenv("ALERT_MAX_PERCENT", "15")),
            "deduplication_minutes": int(os.getenv("ALERT_DEDUPLICATION_MINUTES", "30")),
        },
        "telegram": {
            "configured": is_telegram_configured(),
        },
        "database_counts": {
            "events": db.query(Event).count(),
            "odds_snapshots": db.query(OddsSnapshot).count(),
            "alerts": db.query(Alert).count(),
            "notification_logs": db.query(NotificationLog).count(),
        },
    }
