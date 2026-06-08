import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Event, MonitoredMarket, NotificationLog, OddsSnapshot
from app.services.telegram_notifier import (
    get_active_telegram_recipients,
    is_telegram_configured,
)
from app.services.alert_settings_service import get_or_create_alert_settings
from app.services.scheduler_settings_service import get_or_create_scheduler_settings
from app.services.odds_scheduler import odds_scheduler
from app.services.provider_bookmaker_settings_service import get_configured_bookmakers
from app.services.provider_usage_service import get_provider_usage_status
from app.services.provider_plan_settings_service import (
    estimate_provider_hourly_requests,
    get_active_mapped_competitions_count,
    get_or_create_provider_plan_settings,
)


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    bookmakers = get_configured_bookmakers(db)

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
            "loop_running": odds_scheduler.is_running(),
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



@router.get("/readiness")
def get_system_readiness(db: Session = Depends(get_db)):
    scheduler_settings = get_or_create_scheduler_settings(db)
    provider_plan = get_or_create_provider_plan_settings(db)
    bookmakers = get_configured_bookmakers(db)
    provider_usage = get_provider_usage_status(db)

    active_mapped_competitions_count = get_active_mapped_competitions_count(db)
    usage_estimate = estimate_provider_hourly_requests(
        poll_interval_seconds=scheduler_settings.poll_interval_seconds,
        event_limit=scheduler_settings.event_limit,
        active_mapped_competitions_count=active_mapped_competitions_count,
    )

    estimated_requests_per_hour = usage_estimate["estimated_requests_per_hour"]
    plan_api_ok = (
        True
        if provider_plan.hourly_request_limit is None
        else estimated_requests_per_hour <= provider_plan.hourly_request_limit
    )

    bookmaker_ok = (
        len(bookmakers) > 0
        and len(bookmakers) <= provider_plan.max_bookmakers
    )

    monitored_markets_count = db.query(MonitoredMarket).count()
    active_markets_count = (
        db.query(MonitoredMarket)
        .filter(MonitoredMarket.is_active.is_(True))
        .count()
    )
    markets_ok = active_markets_count > 0 or monitored_markets_count == 0

    competitions_ok = active_mapped_competitions_count > 0

    telegram_configured = is_telegram_configured()
    active_telegram_recipients = get_active_telegram_recipients(db)
    telegram_ok = telegram_configured and len(active_telegram_recipients) > 0

    provider_usage_ok = (
        not provider_usage["limit_reached"]
        and not provider_usage["cooldown_active"]
    )

    checks = {
        "provider_usage": {
            "ok": provider_usage_ok,
            "requests_used_last_hour": provider_usage["requests_used_last_hour"],
            "requests_remaining": provider_usage["requests_remaining"],
            "limit_reached": provider_usage["limit_reached"],
            "cooldown_active": provider_usage["cooldown_active"],
            "cooldown_until": provider_usage["cooldown_until"],
            "message": provider_usage["message"],
        },
        "provider_plan": {
            "ok": plan_api_ok,
            "plan_name": provider_plan.plan_name,
            "hourly_request_limit": provider_plan.hourly_request_limit,
            "estimated_requests_per_hour": estimated_requests_per_hour,
            "message": (
                "Piano API compatibile con la configurazione corrente."
                if plan_api_ok
                else "La stima richieste/ora supera il limite del Piano API."
            ),
        },
        "bookmakers": {
            "ok": bookmaker_ok,
            "configured": bookmakers,
            "bookmaker_count": len(bookmakers),
            "max_bookmakers": provider_plan.max_bookmakers,
            "message": (
                "Bookmaker compatibili con il Piano API."
                if bookmaker_ok
                else "I bookmaker configurati superano il limite del Piano API."
            ),
        },
        "competitions": {
            "ok": competitions_ok,
            "active_mapped_competitions_count": active_mapped_competitions_count,
            "message": (
                "Almeno un campionato attivo e mappato è disponibile."
                if competitions_ok
                else "Nessun campionato attivo e mappato disponibile."
            ),
        },
        "markets": {
            "ok": markets_ok,
            "monitored_markets_count": monitored_markets_count,
            "active_markets_count": active_markets_count,
            "message": (
                "Mercati disponibili per il monitoraggio."
                if markets_ok
                else "Nessun mercato attivo disponibile."
            ),
        },
        "telegram": {
            "ok": telegram_ok,
            "configured": telegram_configured,
            "active_recipients_count": len(active_telegram_recipients),
            "message": (
                "Telegram configurato con almeno un destinatario attivo."
                if telegram_ok
                else "Telegram non è pronto: verifica token e destinatari attivi."
            ),
        },
        "scheduler": {
            "ok": scheduler_settings.enabled,
            "enabled": scheduler_settings.enabled,
            "poll_interval_seconds": scheduler_settings.poll_interval_seconds,
            "event_limit": scheduler_settings.event_limit,
            "loop_running": odds_scheduler.is_running(),
            "message": (
                "Scheduler acceso."
                if scheduler_settings.enabled
                else "Scheduler spento: nessun controllo automatico verrà eseguito."
            ),
        },
    }

    blocking_checks = [
        "provider_usage",
        "provider_plan",
        "bookmakers",
        "competitions",
        "markets",
        "telegram",
    ]

    issues = [
        checks[key]["message"]
        for key in blocking_checks
        if not checks[key]["ok"]
    ]

    warnings = []
    if not scheduler_settings.enabled:
        warnings.append(checks["scheduler"]["message"])

    ready = len(issues) == 0
    automatic_monitoring_ready = ready and scheduler_settings.enabled

    return {
        "ready": ready,
        "automatic_monitoring_ready": automatic_monitoring_ready,
        "scheduler_enabled": scheduler_settings.enabled,
        "checks": checks,
        "issues": issues,
        "warnings": warnings,
    }



@router.get("/provider-usage")
def get_provider_usage(db: Session = Depends(get_db)):
    return get_provider_usage_status(db)
