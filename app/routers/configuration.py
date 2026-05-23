import os
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Competition, MonitoredCompetition, MonitoredMarket, NotificationRecipient
from app.schemas import (
    CompetitionProviderMappingUpdate,
    MonitoredCompetitionCreate,
    MonitoredCompetitionResponse,
    MonitoredMarketCreate,
    MonitoredMarketResponse,
    NotificationRecipientCreate,
    NotificationRecipientResponse,
)
from app.services.odds_api_io_provider import OddsApiIoProvider, classify_provider_error
from app.services.telegram_notifier import (
    get_active_telegram_recipients,
    send_telegram_message,
    sync_telegram_recipients_from_telegram,
)


router = APIRouter(prefix="/configuration", tags=["configuration"])
TELEGRAM_TEST_MESSAGE = (
    "OddSignal - test notifiche Telegram. Se ricevi questo messaggio, "
    "il bot online è configurato correttamente."
)

MARKET_CANONICAL_LABELS = {
    "ML": "1X2",
    "Moneyline": "1X2",
    "1X2": "1X2",
    "Double Chance": "Doppia chance",
    "Doppia chance": "Doppia chance",
    "Draw No Bet": "Pareggio escluso",
    "Pareggio escluso": "Pareggio escluso",
    "Both Teams To Score": "Goal/No Goal",
    "Goal/No Goal": "Goal/No Goal",
    "Spread": "Handicap asiatico",
    "Asian Handicap": "Handicap asiatico",
    "Handicap asiatico": "Handicap asiatico",
    "Handicap principale": "Handicap asiatico",
    "European Handicap": "Handicap europeo",
    "Handicap europeo": "Handicap europeo",
    "Correct Score": "Risultato esatto",
    "Risultato esatto": "Risultato esatto",
    "1st Half Result": "Risultato primo tempo",
    "Risultato primo tempo": "Risultato primo tempo",
    "Half Time/Full Time": "Primo tempo/finale",
    "Primo tempo/finale": "Primo tempo/finale",
    "Corners Totals": "Totale corner",
    "Totale corner": "Totale corner",
    "Corners Spread": "Handicap corner",
    "Handicap corner": "Handicap corner",
    "Cards Totals": "Totale cartellini",
    "Bookings Totals": "Totale cartellini",
    "Totale cartellini": "Totale cartellini",
    "Anytime Goalscorer": "Marcatori",
    "Marcatori": "Marcatori",
    "First Goalscorer": "Primo marcatore",
    "Primo marcatore": "Primo marcatore",
    "Both Teams To Score 1st Half": "Entrambe segnano nel primo tempo",
    "Entrambe segnano nel primo tempo": "Entrambe segnano nel primo tempo",
    "Entrambe le squadre segnano primo tempo": "Entrambe segnano nel primo tempo",
}


def _canonical_market_name(market_name: str) -> str:
    clean_name = (market_name or "").strip()
    if clean_name.startswith("Totals "):
        return "Over/Under " + clean_name.replace("Totals ", "", 1).strip()
    if clean_name.startswith("Over/Under "):
        return clean_name
    return MARKET_CANONICAL_LABELS.get(clean_name, clean_name)


def _market_aliases_for_canonical(canonical_name: str) -> List[str]:
    aliases = [
        alias
        for alias, label in MARKET_CANONICAL_LABELS.items()
        if label == canonical_name
    ]

    if canonical_name.startswith("Over/Under "):
        line = canonical_name.replace("Over/Under ", "", 1).strip()
        aliases.extend([canonical_name, "Totals " + line])

    aliases.append(canonical_name)
    return sorted(set(aliases))


def _market_response(item: MonitoredMarket, canonical_name: str, is_active: bool):
    return {
        "id": item.id,
        "market_name": canonical_name,
        "is_active": is_active,
        "created_at": item.created_at,
    }


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


@router.put("/competitions/provider-mapping")
def update_competition_provider_mapping(
    payload: CompetitionProviderMappingUpdate,
    db: Session = Depends(get_db),
):
    competition_name = payload.competition_name.strip()
    provider_league_slug = payload.provider_league_slug.strip()
    country = payload.country.strip() if payload.country else None

    if not competition_name:
        raise HTTPException(status_code=400, detail="Il nome campionato è obbligatorio.")

    if not provider_league_slug:
        raise HTTPException(status_code=400, detail="Lo slug provider è obbligatorio.")

    competition = db.query(Competition).filter(Competition.name == competition_name).first()

    if competition:
        competition.provider_league_slug = provider_league_slug
        if country and competition.country in {None, "", "Unknown"}:
            competition.country = country
    else:
        competition = Competition(
            name=competition_name,
            country=country or "Unknown",
            provider_league_slug=provider_league_slug,
        )
        db.add(competition)

    monitored = (
        db.query(MonitoredCompetition)
        .filter(MonitoredCompetition.competition_name == competition_name)
        .first()
    )

    if monitored:
        monitored.provider_league_slug = provider_league_slug
        if country:
            monitored.country = country

    db.commit()
    db.refresh(competition)

    return {
        "name": competition.name,
        "country": competition.country,
        "provider_league_slug": competition.provider_league_slug,
        "is_monitored": monitored is not None,
        "is_active": monitored.is_active if monitored else False,
    }


def _country_from_league_name(name: str):
    if not name:
        return "Unknown"

    if " - " in name:
        return name.split(" - ", 1)[0].strip() or "Unknown"

    return "Unknown"


@router.post("/provider-leagues/refresh")
def refresh_provider_leagues(db: Session = Depends(get_db)):
    try:
        provider = OddsApiIoProvider(
            bookmakers_csv=get_configured_bookmakers_csv(db),
            usage_db=db,
        )
        provider_leagues = provider.get_leagues()
    except RuntimeError as exc:
        status_code, detail = classify_provider_error(exc)
        raise HTTPException(status_code=status_code, detail=detail) from exc

    leagues_upserted = 0
    monitored_updated = 0
    leagues = []

    for league in provider_leagues:
        league_name = league.get("name")
        league_slug = league.get("slug")

        if not league_name or not league_slug:
            continue

        country = _country_from_league_name(league_name)

        competition = db.query(Competition).filter(Competition.name == league_name).first()

        if competition:
            competition.provider_league_slug = league_slug
            if competition.country in {None, "", "Unknown"}:
                competition.country = country
        else:
            competition = Competition(
                name=league_name,
                country=country,
                provider_league_slug=league_slug,
            )
            db.add(competition)

        monitored = (
            db.query(MonitoredCompetition)
            .filter(MonitoredCompetition.competition_name == league_name)
            .first()
        )

        if monitored:
            monitored.provider_league_slug = league_slug
            if not monitored.country or monitored.country == "Unknown":
                monitored.country = country
            monitored_updated += 1

        leagues_upserted += 1
        leagues.append(
            {
                "name": league_name,
                "country": country,
                "provider_league_slug": league_slug,
                "events_count": league.get("eventsCount"),
            }
        )

    db.commit()

    return {
        "provider": "odds_api_io",
        "sport": "football",
        "leagues_received": len(provider_leagues),
        "leagues_upserted": leagues_upserted,
        "monitored_updated": monitored_updated,
        "leagues": leagues,
    }


@router.post("/provider-competitions/refresh")
def refresh_provider_competitions(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    try:
        return refresh_provider_competitions_from_provider(db=db, limit=limit)
    except RuntimeError as exc:
        status_code, detail = classify_provider_error(exc)
        raise HTTPException(status_code=status_code, detail=detail) from exc


def refresh_provider_competitions_from_provider(db, limit: int = 10):
    safe_limit = max(1, min(limit, 50))

    provider = OddsApiIoProvider(
        bookmakers_csv=get_configured_bookmakers_csv(db),
        usage_db=db,
    )
    first_bookmaker = provider.bookmakers.split(",")[0].strip()
    provider_events = provider.get_events(
        limit=safe_limit,
        bookmaker=first_bookmaker,
    )
    events = [provider.normalize_event(event) for event in provider_events]

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
    grouped_markets = {}
    for item in db.query(MonitoredMarket).order_by(MonitoredMarket.market_name).all():
        canonical_name = _canonical_market_name(item.market_name)
        group = grouped_markets.setdefault(
            canonical_name,
            {
                "item": item,
                "is_active": False,
            },
        )
        if item.market_name == canonical_name:
            group["item"] = item
        group["is_active"] = group["is_active"] or item.is_active

    return [
        _market_response(group["item"], canonical_name, group["is_active"])
        for canonical_name, group in sorted(grouped_markets.items())
    ]


@router.post(
    "/monitored-markets",
    response_model=MonitoredMarketResponse,
)
def upsert_monitored_market(
    payload: MonitoredMarketCreate,
    db: Session = Depends(get_db),
):
    canonical_name = _canonical_market_name(payload.market_name)
    aliases = _market_aliases_for_canonical(canonical_name)
    existing_items = (
        db.query(MonitoredMarket)
        .filter(MonitoredMarket.market_name.in_(aliases))
        .all()
    )

    if existing_items:
        canonical_item = next(
            (item for item in existing_items if item.market_name == canonical_name),
            existing_items[0],
        )
        if canonical_item.market_name != canonical_name:
            canonical_item.market_name = canonical_name

        for item in existing_items:
            item.is_active = payload.is_active

        db.commit()
        db.refresh(canonical_item)
        return _market_response(canonical_item, canonical_name, payload.is_active)

    item = MonitoredMarket(
        market_name=canonical_name,
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

    canonical_name = _canonical_market_name(item.market_name)
    aliases = _market_aliases_for_canonical(canonical_name)
    group_items = (
        db.query(MonitoredMarket)
        .filter(MonitoredMarket.market_name.in_(aliases))
        .all()
    )

    canonical_item = next(
        (market for market in group_items if market.market_name == canonical_name),
        item,
    )
    if canonical_item.market_name != canonical_name:
        canonical_item.market_name = canonical_name

    for market in group_items:
        market.is_active = is_active

    db.commit()
    db.refresh(canonical_item)

    return _market_response(canonical_item, canonical_name, is_active)


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


@router.post("/telegram-recipients/sync")
def sync_telegram_recipients(db: Session = Depends(get_db)):
    existing_telegram_values = {
        item.recipient_value
        for item in db.query(NotificationRecipient)
        .filter(NotificationRecipient.channel == "telegram")
        .all()
    }

    result = sync_telegram_recipients_from_telegram(db)

    if result["status"] == "skipped" and result["error"] == "telegram_not_configured":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "telegram_not_configured",
                "message": "Configura TELEGRAM_BOT_TOKEN prima di rilevare account Telegram.",
            },
        )

    if result["status"] == "failed" and result["error"] == "telegram_request_failed":
        raise HTTPException(
            status_code=502,
            detail={
                "error": "telegram_request_failed",
                "message": "Impossibile contattare Telegram. Riprova tra poco.",
            },
        )

    if result["status"] == "failed" and result["error"] == "telegram_api_error":
        raise HTTPException(
            status_code=502,
            detail={
                "error": "telegram_api_error",
                "message": "Telegram ha rifiutato la richiesta. Verifica il token del bot.",
            },
        )

    telegram_recipients = (
        db.query(NotificationRecipient)
        .filter(NotificationRecipient.channel == "telegram")
        .all()
    )

    new_recipients_count = len(
        [
            item
            for item in telegram_recipients
            if item.recipient_value not in existing_telegram_values
        ]
    )

    active_recipients_count = len(
        [item for item in telegram_recipients if item.status == "active" and item.is_active]
    )
    pending_recipients_count = len(
        [item for item in telegram_recipients if item.status == "pending"]
    )

    return {
        "synced_count": result["synced_count"],
        "new_recipients_count": new_recipients_count,
        "total_telegram_recipients_count": len(telegram_recipients),
        "active_recipients_count": active_recipients_count,
        "pending_recipients_count": pending_recipients_count,
        "recipients": result["recipients"],
    }


@router.post("/telegram-test-message")
def send_telegram_test_message(db: Session = Depends(get_db)):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "telegram_not_configured",
                "message": "Configura TELEGRAM_BOT_TOKEN prima di inviare il test Telegram.",
            },
        )

    recipients = get_active_telegram_recipients(db, include_fallback=False)
    if not recipients:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "telegram_no_active_recipients",
                "message": "Nessun destinatario Telegram attivo configurato.",
            },
        )

    results = [
        send_telegram_message(
            bot_token=bot_token,
            recipient=recipient,
            message=TELEGRAM_TEST_MESSAGE,
        )
        for recipient in recipients
    ]

    sent = len([item for item in results if item["status"] == "sent"])
    failed = len([item for item in results if item["status"] == "failed"])

    return {
        "status": "completed",
        "channel": "telegram",
        "message": "Test Telegram completato.",
        "recipients_count": len(recipients),
        "sent": sent,
        "failed": failed,
        "results": results,
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


from app.schemas import AlertSettingResponse, AlertSettingUpdate, SchedulerSettingResponse, SchedulerSettingUpdate, ProviderPlanSettingResponse, ProviderPlanSettingUpdate, ProviderBookmakerSettingResponse, ProviderBookmakerSettingUpdate
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
    validate_scheduler_against_provider_plan,
    validate_bookmakers_against_provider_plan,
)
from app.services.provider_bookmaker_settings_service import (
    bookmakers_from_csv,
    get_configured_bookmakers_csv,
    get_or_create_provider_bookmaker_settings,
    update_provider_bookmaker_settings,
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
        validate_scheduler_against_provider_plan(
            db=db,
            enabled=payload.enabled,
            poll_interval_seconds=payload.poll_interval_seconds,
            event_limit=payload.event_limit,
        )
        validate_bookmakers_against_provider_plan(
            db=db,
            enabled=payload.enabled,
        )
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



def _provider_bookmaker_response(db):
    item = get_or_create_provider_bookmaker_settings(db)
    plan = get_or_create_provider_plan_settings(db)
    bookmakers = bookmakers_from_csv(item.bookmakers_csv)

    return {
        "id": item.id,
        "bookmakers_csv": item.bookmakers_csv,
        "bookmakers": bookmakers,
        "bookmaker_count": len(bookmakers),
        "max_bookmakers": plan.max_bookmakers,
        "exceeds_bookmaker_limit": len(bookmakers) > plan.max_bookmakers,
        "created_at": item.created_at,
    }


@router.get("/provider-bookmaker-settings", response_model=ProviderBookmakerSettingResponse)
def get_provider_bookmaker_settings(db: Session = Depends(get_db)):
    return _provider_bookmaker_response(db)


@router.put("/provider-bookmaker-settings", response_model=ProviderBookmakerSettingResponse)
def put_provider_bookmaker_settings(
    payload: ProviderBookmakerSettingUpdate,
    db: Session = Depends(get_db),
):
    try:
        update_provider_bookmaker_settings(
            db=db,
            bookmakers_csv=payload.bookmakers_csv,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _provider_bookmaker_response(db)
