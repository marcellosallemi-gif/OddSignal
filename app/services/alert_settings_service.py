import os
from datetime import datetime, timezone

from app.models import AlertSetting


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_or_create_alert_settings(db) -> AlertSetting:
    settings = db.query(AlertSetting).order_by(AlertSetting.id.asc()).first()

    if settings:
        return settings

    settings = AlertSetting(
        min_percent=float(os.getenv("ALERT_MIN_PERCENT", "8")),
        max_percent=float(os.getenv("ALERT_MAX_PERCENT", "15")),
        critical_percent=float(os.getenv("ALERT_MAX_PERCENT", "15")),
        deduplication_minutes=int(os.getenv("ALERT_DEDUPLICATION_MINUTES", "30")),
        created_at=_utc_now_naive(),
    )

    db.add(settings)
    db.flush()

    return settings


def update_alert_settings(
    db,
    min_percent: float,
    max_percent: float,
    critical_percent: float,
    deduplication_minutes: int,
) -> AlertSetting:
    if min_percent <= 0:
        raise ValueError("min_percent must be greater than 0")

    if max_percent < min_percent:
        raise ValueError("max_percent must be greater than or equal to min_percent")

    if critical_percent < max_percent:
        raise ValueError("critical_percent must be greater than or equal to max_percent")

    if deduplication_minutes < 0:
        raise ValueError("deduplication_minutes must be greater than or equal to 0")

    settings = get_or_create_alert_settings(db)

    settings.min_percent = min_percent
    settings.max_percent = max_percent
    settings.critical_percent = critical_percent
    settings.deduplication_minutes = deduplication_minutes

    db.commit()
    db.refresh(settings)

    return settings
