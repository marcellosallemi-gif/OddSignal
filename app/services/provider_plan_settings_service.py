import os
from datetime import datetime, timezone

from app.models import ProviderPlanSetting, MonitoredCompetition


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _default_plan_name() -> str:
    return os.getenv("PROVIDER_PLAN_NAME", "Free")


def _default_hourly_request_limit():
    raw_value = os.getenv("PROVIDER_HOURLY_REQUEST_LIMIT", "100")

    if str(raw_value).lower() in {"", "0", "none", "unlimited", "illimitato"}:
        return None

    try:
        value = int(raw_value)
    except ValueError:
        return 100

    if value < 1:
        return None

    return value


def _default_max_bookmakers() -> int:
    try:
        value = int(os.getenv("PROVIDER_MAX_BOOKMAKERS", "2"))
    except ValueError:
        value = 2

    return max(value, 1)


def validate_provider_plan_settings(
    plan_name: str,
    hourly_request_limit,
    max_bookmakers: int,
):
    if not plan_name or not plan_name.strip():
        raise ValueError("Il nome piano provider è obbligatorio.")

    if hourly_request_limit is not None and hourly_request_limit < 1:
        raise ValueError("Il limite richieste/ora deve essere almeno 1 oppure nullo per illimitato.")

    if max_bookmakers < 1:
        raise ValueError("Il numero massimo di bookmaker deve essere almeno 1.")

    if max_bookmakers > 100:
        raise ValueError("Il numero massimo di bookmaker non può superare 100.")


def get_or_create_provider_plan_settings(db):
    item = db.query(ProviderPlanSetting).order_by(ProviderPlanSetting.id).first()

    if item:
        return item

    item = ProviderPlanSetting(
        plan_name=_default_plan_name(),
        hourly_request_limit=_default_hourly_request_limit(),
        max_bookmakers=_default_max_bookmakers(),
        created_at=_utc_now_naive(),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def update_provider_plan_settings(
    db,
    plan_name: str,
    hourly_request_limit,
    max_bookmakers: int,
):
    validate_provider_plan_settings(
        plan_name=plan_name,
        hourly_request_limit=hourly_request_limit,
        max_bookmakers=max_bookmakers,
    )

    item = get_or_create_provider_plan_settings(db)
    item.plan_name = plan_name.strip()
    item.hourly_request_limit = hourly_request_limit
    item.max_bookmakers = max_bookmakers

    db.commit()
    db.refresh(item)

    return item


def estimate_provider_hourly_requests(
    poll_interval_seconds: int,
    event_limit: int,
    active_mapped_competitions_count: int,
):
    if poll_interval_seconds <= 0:
        return None

    cycles_per_hour = 3600 / poll_interval_seconds
    estimated_requests_per_cycle = active_mapped_competitions_count + event_limit
    estimated_requests_per_hour = cycles_per_hour * estimated_requests_per_cycle

    return {
        "cycles_per_hour": round(cycles_per_hour, 2),
        "estimated_requests_per_cycle": estimated_requests_per_cycle,
        "estimated_requests_per_hour": round(estimated_requests_per_hour, 2),
    }


def get_active_mapped_competitions_count(db):
    return (
        db.query(MonitoredCompetition)
        .filter(
            MonitoredCompetition.is_active == True,  # noqa: E712
            MonitoredCompetition.provider_league_slug.isnot(None),
        )
        .count()
    )



def validate_scheduler_against_provider_plan(
    db,
    enabled: bool,
    poll_interval_seconds: int,
    event_limit: int,
):
    if not enabled:
        return None

    plan = get_or_create_provider_plan_settings(db)

    if plan.hourly_request_limit is None:
        return None

    active_mapped_competitions_count = get_active_mapped_competitions_count(db)
    estimate = estimate_provider_hourly_requests(
        poll_interval_seconds=poll_interval_seconds,
        event_limit=event_limit,
        active_mapped_competitions_count=active_mapped_competitions_count,
    )

    estimated_requests_per_hour = estimate["estimated_requests_per_hour"]

    if estimated_requests_per_hour <= plan.hourly_request_limit:
        return None

    raise ValueError(
        "Configurazione scheduler troppo aggressiva per il piano API {plan_name}: "
        "stima {estimated} richieste/ora su limite {limit} richieste/ora. "
        "Aumenta l’intervallo scheduler, riduci eventi per ciclo o riduci campionati attivi."
        .format(
            plan_name=plan.plan_name,
            estimated=estimated_requests_per_hour,
            limit=plan.hourly_request_limit,
        )
    )
