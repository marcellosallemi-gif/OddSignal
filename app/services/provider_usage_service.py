from datetime import datetime, timedelta, timezone

from app.models import ProviderApiRequestLog
from app.services.provider_plan_settings_service import get_or_create_provider_plan_settings


PROVIDER_NAME = "odds_api_io"


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _window_start(now=None):
    current = now or _utc_now_naive()
    return current - timedelta(hours=1)


def count_provider_requests_last_hour(db, now=None):
    return (
        db.query(ProviderApiRequestLog)
        .filter(
            ProviderApiRequestLog.provider == PROVIDER_NAME,
            ProviderApiRequestLog.created_at >= _window_start(now),
        )
        .count()
    )


def get_provider_usage_status(db):
    plan = get_or_create_provider_plan_settings(db)
    used = count_provider_requests_last_hour(db)

    if plan.hourly_request_limit is None:
        return {
            "provider": PROVIDER_NAME,
            "hourly_request_limit": None,
            "requests_used_last_hour": used,
            "requests_remaining": None,
            "limit_reached": False,
            "message": "Piano API senza blocco locale richieste/ora.",
        }

    remaining = max(plan.hourly_request_limit - used, 0)
    limit_reached = used >= plan.hourly_request_limit

    return {
        "provider": PROVIDER_NAME,
        "hourly_request_limit": plan.hourly_request_limit,
        "requests_used_last_hour": used,
        "requests_remaining": remaining,
        "limit_reached": limit_reached,
        "message": (
            "Limite richieste/ora disponibile."
            if not limit_reached
            else "Limite richieste/ora raggiunto localmente. Attendi il reset orario o aggiorna il Piano API."
        ),
    }


def ensure_provider_request_allowed(db, endpoint: str):
    status = get_provider_usage_status(db)

    if status["limit_reached"]:
        raise RuntimeError(
            "Provider API local hourly limit reached: {used}/{limit} requests used. "
            "Endpoint blocked before calling Odds-API.io: {endpoint}."
            .format(
                used=status["requests_used_last_hour"],
                limit=status["hourly_request_limit"],
                endpoint=endpoint,
            )
        )


def record_provider_request(db, endpoint: str, status_code=None):
    item = ProviderApiRequestLog(
        provider=PROVIDER_NAME,
        endpoint=endpoint,
        status_code=status_code,
        created_at=_utc_now_naive(),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item
