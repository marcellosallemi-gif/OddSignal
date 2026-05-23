from datetime import datetime, timedelta, timezone

from app.models import ProviderApiRateLimitState, ProviderApiRequestLog
from app.services.provider_plan_settings_service import get_or_create_provider_plan_settings


PROVIDER_NAME = "odds_api_io"


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _current_hour_window(now=None):
    current = now or _utc_now_naive()
    window_start = current.replace(minute=0, second=0, microsecond=0)
    return window_start, window_start + timedelta(hours=1)


def _window_start(now=None):
    return _current_hour_window(now)[0]


def count_provider_requests_current_hour(db, now=None):
    window_start, window_end = _current_hour_window(now)
    return (
        db.query(ProviderApiRequestLog)
        .filter(
            ProviderApiRequestLog.provider == PROVIDER_NAME,
            ProviderApiRequestLog.created_at >= window_start,
            ProviderApiRequestLog.created_at < window_end,
        )
        .count()
    )


def count_provider_requests_last_hour(db, now=None):
    return count_provider_requests_current_hour(db, now=now)


def get_provider_usage_status(db, now=None):
    current = now or _utc_now_naive()
    window_start, window_reset_at = _current_hour_window(current)
    plan = get_or_create_provider_plan_settings(db)
    used = count_provider_requests_current_hour(db, now=current)
    cooldown = get_active_provider_rate_limit_cooldown(db, now=current)

    cooldown_active = cooldown is not None
    cooldown_until = cooldown.blocked_until if cooldown else None
    cooldown_reason = cooldown.reason if cooldown else None

    if plan.hourly_request_limit is None:
        return {
            "provider": PROVIDER_NAME,
            "hourly_request_limit": None,
            "requests_used_last_hour": used,
            "requests_used_current_hour": used,
            "requests_remaining": None,
            "current_window_start": window_start,
            "current_window_reset_at": window_reset_at,
            "limit_reached": False,
            "cooldown_active": cooldown_active,
            "cooldown_until": cooldown_until,
            "cooldown_reason": cooldown_reason,
            "message": (
                "Provider in cooldown locale per rate limit. Attendi il reset prima di nuove chiamate."
                if cooldown_active
                else "Piano API senza blocco locale richieste/ora."
            ),
        }

    remaining = max(plan.hourly_request_limit - used, 0)
    limit_reached = used >= plan.hourly_request_limit

    return {
        "provider": PROVIDER_NAME,
        "hourly_request_limit": plan.hourly_request_limit,
        "requests_used_last_hour": used,
        "requests_used_current_hour": used,
        "requests_remaining": remaining,
        "current_window_start": window_start,
        "current_window_reset_at": window_reset_at,
        "limit_reached": limit_reached,
        "cooldown_active": cooldown_active,
        "cooldown_until": cooldown_until,
        "cooldown_reason": cooldown_reason,
        "message": (
            "Provider in cooldown locale per rate limit. Attendi il reset prima di nuove chiamate."
            if cooldown_active
            else (
                "Limite richieste/ora disponibile."
                if not limit_reached
                else "Limite richieste/ora raggiunto localmente. Attendi il reset orario o aggiorna il Piano API."
            )
        ),
    }


def ensure_provider_request_allowed(db, endpoint: str):
    status = get_provider_usage_status(db)

    if status["cooldown_active"]:
        raise RuntimeError(
            "Provider API cooldown active until {blocked_until}. "
            "Endpoint blocked before calling Odds-API.io: {endpoint}."
            .format(
                blocked_until=status["cooldown_until"],
                endpoint=endpoint,
            )
        )

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



def get_provider_rate_limit_state(db):
    return (
        db.query(ProviderApiRateLimitState)
        .filter(ProviderApiRateLimitState.provider == PROVIDER_NAME)
        .order_by(ProviderApiRateLimitState.id)
        .first()
    )


def get_active_provider_rate_limit_cooldown(db, now=None):
    current = now or _utc_now_naive()
    item = get_provider_rate_limit_state(db)

    if not item:
        return None

    if item.blocked_until <= current:
        return None

    return item


def activate_provider_rate_limit_cooldown(
    db,
    endpoint: str,
    cooldown_minutes: int = 60,
):
    current = _utc_now_naive()
    blocked_until = current + timedelta(minutes=cooldown_minutes)

    item = get_provider_rate_limit_state(db)

    reason = "Odds-API.io rate limit reached while calling {endpoint}".format(
        endpoint=endpoint,
    )

    if item:
        item.blocked_until = blocked_until
        item.reason = reason
        item.updated_at = current
    else:
        item = ProviderApiRateLimitState(
            provider=PROVIDER_NAME,
            blocked_until=blocked_until,
            reason=reason,
            created_at=current,
            updated_at=current,
        )
        db.add(item)

    db.commit()
    db.refresh(item)

    return item
