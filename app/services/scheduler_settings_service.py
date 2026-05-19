import os
from datetime import datetime, timezone

from app.models import SchedulerSetting


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_truthy(value: str) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def is_local_debug_environment() -> bool:
    return (
        os.getenv("APP_ENV", "local") == "local"
        or _is_truthy(os.getenv("APP_DEBUG", "false"))
    )


def minimum_poll_interval_seconds() -> int:
    return 3 if is_local_debug_environment() else 30


def _default_enabled() -> bool:
    return os.getenv("ODDS_SCHEDULER_ENABLED", "0") == "1"


def _default_poll_interval_seconds() -> int:
    try:
        value = int(os.getenv("ODDS_POLL_INTERVAL_SECONDS", "300"))
    except ValueError:
        value = 300

    return max(value, minimum_poll_interval_seconds())


def _default_event_limit() -> int:
    try:
        value = int(os.getenv("ODDS_SCHEDULER_EVENT_LIMIT", "1"))
    except ValueError:
        value = 1

    return min(max(value, 1), 10)


def validate_scheduler_settings(
    poll_interval_seconds: int,
    event_limit: int,
):
    minimum_interval = minimum_poll_interval_seconds()

    if poll_interval_seconds < minimum_interval:
        raise ValueError(
            "La frequenza controllo non può essere inferiore a {} secondi.".format(
                minimum_interval
            )
        )

    if poll_interval_seconds > 86400:
        raise ValueError("La frequenza controllo non può superare 86400 secondi.")

    if event_limit < 1:
        raise ValueError("Gli eventi per ciclo devono essere almeno 1.")

    if event_limit > 10:
        raise ValueError("Gli eventi per ciclo non possono superare 10.")


def get_or_create_scheduler_settings(db):
    item = db.query(SchedulerSetting).order_by(SchedulerSetting.id).first()

    if item:
        return item

    item = SchedulerSetting(
        enabled=_default_enabled(),
        poll_interval_seconds=_default_poll_interval_seconds(),
        event_limit=_default_event_limit(),
        created_at=_utc_now_naive(),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def update_scheduler_settings(
    db,
    enabled: bool,
    poll_interval_seconds: int,
    event_limit: int,
):
    validate_scheduler_settings(
        poll_interval_seconds=poll_interval_seconds,
        event_limit=event_limit,
    )

    item = get_or_create_scheduler_settings(db)
    item.enabled = enabled
    item.poll_interval_seconds = poll_interval_seconds
    item.event_limit = event_limit

    db.commit()
    db.refresh(item)

    return item
