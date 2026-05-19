import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Event, NotificationLog, OddsSnapshot
from app.services.telegram_notifier import is_telegram_configured
from app.services.alert_settings_service import get_or_create_alert_settings
from app.services.scheduler_settings_service import get_or_create_scheduler_settings


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    bookmakers = [
        bookmaker.strip()
        for bookmaker in os.getenv("ODDS_API_BOOKMAKERS", "").split(",")
        if bookmaker.strip()
    ]

    alert_settings = get_or_create_alert_settings(db)
    scheduler_settings = get_or_create_scheduler_settings(db)

    return {
        "provider": os.getenv("ODDS_PROVIDER", "unknown"),
        "sport": os.getenv("ODDS_API_SPORT", "unknown"),
        "bookmakers": bookmakers,
        "scheduler": {
            "enabled": scheduler_settings.enabled,
            "poll_interval_seconds": scheduler_settings.poll_interval_seconds,
            "event_limit": scheduler_settings.event_limit,
        },
        "alerts": {
            "min_percent": alert_settings.min_percent,
            "max_percent": alert_settings.max_percent,
            "critical_percent": alert_settings.critical_percent,
            "deduplication_minutes": alert_settings.deduplication_minutes,
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
