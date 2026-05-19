import os
from datetime import datetime, timezone
from typing import List

import httpx

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Competition, MonitoredCompetition, MonitoredMarket, NotificationRecipient
from app.schemas import (
    MonitoredCompetitionCreate,
    MonitoredCompetitionResponse,
    MonitoredMarketCreate,
    MonitoredMarketResponse,
    NotificationRecipientCreate,
    NotificationRecipientResponse,
)
from app.services.odds_api_io_provider import OddsApiIoProvider, classify_provider_error


router = APIRouter(prefix="/configuration", tags=["configuration"])


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/available-competitions")
def get_available_competitions(db: Session = Depends(get_db)):
    competitions = db.query(Competition).order_by(Competition.name).all()

    monitored = {
        item.competition_name: item
        for item in db.query(MonitoredCompetition).all()
    }

    return [
        {
            "name": competition.name,
            "country": competition.country,
            "provider_league_slug": competition.provider_league_slug,
            "is_monitored": competition.name in monitored,
            "is_active": monitored[competition.name].is_active
            if competition.name in monitored
            else False,
            "provider_league_slug": monitored[competition.name].provider_league_slug
            if competition.name in monitored
            else competition.provider_league_slug,
        }
        for competition in competitions
    ]


@router.post("/provider-competitions/refresh")
def refresh_provider_competitions(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 50))

    try:
        provider = OddsApiIoProvider()
        first_bookmaker = provider.bookmakers.split(",")[0].strip()
        provider_events = provider.get_events(
            limit=safe_limit,
            bookmaker=first_bookmaker,
        )
        events = [provider.normalize_event(event) for event in provider_events]
    except RuntimeError as exc:
        status_code, detail = classify_provider_error(exc)
        raise HTTPException(status_code=status_code, detail=detail) from exc

    competitions_by_name = {}
    for event in events:
        league_name = event.get("league_name")
        if not league_name:
            continue

        competitions_by_name[league_name] = {
            "name": league_name,
            "provider_league_slug": event.get("league_slug"),
            "country": "Unknown",
        }

    competitions = []
    competitions_upserted = 0

    for item in sorted(competitions_by_name.values(), key=lambda value: value["name"]):
        existing = db.query(Competition).filter(Competition.name == item["name"]).first()

        if existing:
            if item["provider_league_slug"]:
                existing.provider_league_slug = item["provider_league_slug"]
            if not existing.country:
                existing.country = "Unknown"
        else:
            existing = Competition(
                name=item["name"],
                country=item["country"],
                provider_league_slug=item["provider_league_slug"],
            )
            db.add(existing)

        competitions_upserted += 1
        competitions.append(item)

    db.commit()

    return {
        "provider": "odds_api_io",
        "events_received": len(events),
        "competitions_found": len(competitions),
        "competitions_upserted": competitions_upserted,
        "competitions": competitions,
    }


@router.get(
    "/monitored-competitions",
    response_model=List[MonitoredCompetitionResponse],
)
def get_monitored_competitions(db: Session = Depends(get_db)):
    return (
        db.query(MonitoredCompetition)
        .order_by(MonitoredCompetition.competition_name)
        .all()
    )


@router.post(
    "/monitored-competitions",
    response_model=MonitoredCompetitionResponse,
)
def upsert_monitored_competition(
    payload: MonitoredCompetitionCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(MonitoredCompetition)
        .filter(MonitoredCompetition.competition_name == payload.competition_name)
        .first()
    )

    if existing:
        existing.country = payload.country
        existing.provider = payload.provider
        existing.provider_league_slug = payload.provider_league_slug
        existing.is_active = payload.is_active
        db.commit()
        db.refresh(existing)
        return existing

    item = MonitoredCompetition(
        competition_name=payload.competition_name,
        country=payload.country,
        provider=payload.provider,
        provider_league_slug=payload.provider_league_slug,
        is_active=payload.is_active,
        created_at=_utc_now_naive(),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.patch(
    "/monitored-competitions/{competition_id}/toggle",
    response_model=MonitoredCompetitionResponse,
)
def toggle_monitored_competition(
    competition_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
):
    item = db.query(MonitoredCompetition).filter(MonitoredCompetition.id == competition_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Monitored competition not found")

    item.is_active = is_active
    item.status = "active" if is_active else "disabled"
    db.commit()
    db.refresh(item)

    return item


@router.get(
    "/monitored-markets",
    response_model=List[MonitoredMarketResponse],
)
def get_monitored_markets(db: Session = Depends(get_db)):
    return db.query(MonitoredMarket).order_by(MonitoredMarket.market_name).all()


@router.post(
    "/monitored-markets",
    response_model=MonitoredMarketResponse,
)
def upsert_monitored_market(
    payload: MonitoredMarketCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(MonitoredMarket)
        .filter(MonitoredMarket.market_name == payload.market_name)
        .first()
    )

    if existing:
        existing.is_active = payload.is_active
        db.commit()
        db.refresh(existing)
        return existing

    item = MonitoredMarket(
        market_name=payload.market_name,
        is_active=payload.is_active,
        created_at=_utc_now_naive(),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.patch(
    "/monitored-markets/{market_id}/toggle",
    response_model=MonitoredMarketResponse,
)
def toggle_monitored_market(
    market_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
):
    item = db.query(MonitoredMarket).filter(MonitoredMarket.id == market_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Monitored market not found")

    item.is_active = is_active
    item.status = "active" if is_active else "disabled"
    db.commit()
    db.refresh(item)

    return item


@router.get(
    "/notification-recipients",
    response_model=List[NotificationRecipientResponse],
)
def get_notification_recipients(db: Session = Depends(get_db)):
    return (
        db.query(NotificationRecipient)
        .order_by(NotificationRecipient.channel, NotificationRecipient.id)
        .all()
    )


@router.post(
    "/notification-recipients",
    response_model=NotificationRecipientResponse,
)
def create_notification_recipient(
    payload: NotificationRecipientCreate,
    db: Session = Depends(get_db),
):
    if payload.channel not in {"telegram", "phone"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported channel. Use 'telegram' or 'phone'.",
        )

    existing = (
        db.query(NotificationRecipient)
        .filter(
            NotificationRecipient.channel == payload.channel,
            NotificationRecipient.recipient_value == payload.recipient_value,
        )
        .first()
    )

    status = payload.status or ("active" if payload.is_active else "pending")

    if status not in {"pending", "active", "disabled"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported recipient status.",
        )

    if existing:
        existing.label = payload.label
        existing.is_active = payload.is_active
        existing.status = status
        db.commit()
        db.refresh(existing)
        return existing

    item = NotificationRecipient(
        channel=payload.channel,
        recipient_value=payload.recipient_value,
        label=payload.label,
        is_active=payload.is_active,
        status=status,
        created_at=_utc_now_naive(),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def _telegram_label_from_chat(chat):
    first_name = chat.get("first_name") or ""
    last_name = chat.get("last_name") or ""
    username = chat.get("username")

    full_name = " ".join([part for part in [first_name, last_name] if part]).strip()

    if full_name and username:
        return f"{full_name} (@{username})"

    if username:
        return f"@{username}"

    if full_name:
        return full_name

    return "Account Telegram"


@router.post("/telegram-recipients/sync")
def sync_telegram_recipients(db: Session = Depends(get_db)):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "telegram_not_configured",
                "message": "Configura TELEGRAM_BOT_TOKEN prima di rilevare account Telegram.",
            },
        )

    try:
        response = httpx.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            timeout=15,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "telegram_request_failed",
                "message": "Impossibile contattare Telegram. Riprova tra poco.",
            },
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "telegram_api_error",
                "message": "Telegram ha rifiutato la richiesta. Verifica il token del bot.",
            },
        )

    payload = response.json()
    chats_by_id = {}

    for update in payload.get("result", []):
        message = update.get("message") or {}
        chat = message.get("chat") or {}

        if chat.get("type") != "private":
            continue

        chat_id = chat.get("id")
        if chat_id is None:
            continue

        chats_by_id[str(chat_id)] = chat

    synced = []

    for recipient_value, chat in chats_by_id.items():
        label = _telegram_label_from_chat(chat)

        existing = (
            db.query(NotificationRecipient)
            .filter(
                NotificationRecipient.channel == "telegram",
                NotificationRecipient.recipient_value == recipient_value,
            )
            .first()
        )

        if existing:
            existing.label = label
            recipient = existing
        else:
            recipient = NotificationRecipient(
                channel="telegram",
                recipient_value=recipient_value,
                label=label,
                is_active=False,
                status="pending",
                created_at=_utc_now_naive(),
            )
            db.add(recipient)

        db.flush()
        synced.append(
            {
                "id": recipient.id,
                "label": label,
                "is_active": recipient.is_active,
            }
        )

    db.commit()

    return {
        "synced_count": len(synced),
        "recipients": synced,
    }


@router.patch(
    "/notification-recipients/{recipient_id}/toggle",
    response_model=NotificationRecipientResponse,
)
def toggle_notification_recipient(
    recipient_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
):
    item = db.query(NotificationRecipient).filter(NotificationRecipient.id == recipient_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Notification recipient not found")

    item.is_active = is_active
    item.status = "active" if is_active else "disabled"
    db.commit()
    db.refresh(item)

    return item


from app.schemas import AlertSettingResponse, AlertSettingUpdate, SchedulerSettingResponse, SchedulerSettingUpdate, ProviderPlanSettingResponse, ProviderPlanSettingUpdate
from app.services.alert_settings_service import (
    get_or_create_alert_settings,
    update_alert_settings,
)
from app.services.scheduler_settings_service import (
    get_or_create_scheduler_settings,
    update_scheduler_settings,
)
from app.services.provider_plan_settings_service import (
    estimate_provider_hourly_requests,
    get_active_mapped_competitions_count,
    get_or_create_provider_plan_settings,
    update_provider_plan_settings,
)


@router.get("/alert-settings", response_model=AlertSettingResponse)
def get_alert_settings(db: Session = Depends(get_db)):
    return get_or_create_alert_settings(db)


@router.put("/alert-settings", response_model=AlertSettingResponse)
def put_alert_settings(
    payload: AlertSettingUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_alert_settings(
            db=db,
            min_percent=payload.min_percent,
            max_percent=payload.max_percent,
            critical_percent=payload.critical_percent,
            deduplication_minutes=payload.deduplication_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/scheduler-settings", response_model=SchedulerSettingResponse)
def get_scheduler_settings(db: Session = Depends(get_db)):
    return get_or_create_scheduler_settings(db)


@router.put("/scheduler-settings", response_model=SchedulerSettingResponse)
def put_scheduler_settings(
    payload: SchedulerSettingUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_scheduler_settings(
            db=db,
            enabled=payload.enabled,
            poll_interval_seconds=payload.poll_interval_seconds,
            event_limit=payload.event_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))



def _provider_plan_recommendation(
    hourly_request_limit,
    estimated_requests_per_hour,
):
    if hourly_request_limit is None:
        return "Piano illimitato configurato: nessun blocco interno richieste/ora."

    if estimated_requests_per_hour <= hourly_request_limit:
        return "Configurazione compatibile con il limite richieste/ora impostato."

    return (
        "Configurazione troppo aggressiva per il limite richieste/ora impostato. "
        "Aumenta l’intervallo scheduler, riduci eventi per ciclo o riduci campionati attivi."
    )


def _provider_plan_response(db):
    plan = get_or_create_provider_plan_settings(db)
    scheduler = get_or_create_scheduler_settings(db)
    active_mapped_competitions_count = get_active_mapped_competitions_count(db)

    estimate = estimate_provider_hourly_requests(
        poll_interval_seconds=scheduler.poll_interval_seconds,
        event_limit=scheduler.event_limit,
        active_mapped_competitions_count=active_mapped_competitions_count,
    )

    estimated_requests_per_hour = estimate["estimated_requests_per_hour"]
    exceeds_hourly_limit = (
        False
        if plan.hourly_request_limit is None
        else estimated_requests_per_hour > plan.hourly_request_limit
    )

    return {
        "id": plan.id,
        "plan_name": plan.plan_name,
        "hourly_request_limit": plan.hourly_request_limit,
        "max_bookmakers": plan.max_bookmakers,
        "created_at": plan.created_at,
        "usage_estimate": {
            "active_mapped_competitions_count": active_mapped_competitions_count,
            "poll_interval_seconds": scheduler.poll_interval_seconds,
            "event_limit": scheduler.event_limit,
            "cycles_per_hour": estimate["cycles_per_hour"],
            "estimated_requests_per_cycle": estimate["estimated_requests_per_cycle"],
            "estimated_requests_per_hour": estimated_requests_per_hour,
            "hourly_request_limit": plan.hourly_request_limit,
            "exceeds_hourly_limit": exceeds_hourly_limit,
            "recommendation": _provider_plan_recommendation(
                hourly_request_limit=plan.hourly_request_limit,
                estimated_requests_per_hour=estimated_requests_per_hour,
            ),
        },
    }


@router.get("/provider-plan-settings", response_model=ProviderPlanSettingResponse)
def get_provider_plan_settings(db: Session = Depends(get_db)):
    return _provider_plan_response(db)


@router.put("/provider-plan-settings", response_model=ProviderPlanSettingResponse)
def put_provider_plan_settings(
    payload: ProviderPlanSettingUpdate,
    db: Session = Depends(get_db),
):
    try:
        update_provider_plan_settings(
            db=db,
            plan_name=payload.plan_name,
            hourly_request_limit=payload.hourly_request_limit,
            max_bookmakers=payload.max_bookmakers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _provider_plan_response(db)
