from datetime import datetime, timezone
from typing import List

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
            else None,
        }
        for competition in competitions
    ]


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

    if existing:
        existing.label = payload.label
        existing.is_active = payload.is_active
        db.commit()
        db.refresh(existing)
        return existing

    item = NotificationRecipient(
        channel=payload.channel,
        recipient_value=payload.recipient_value,
        label=payload.label,
        is_active=payload.is_active,
        created_at=_utc_now_naive(),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


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
    db.commit()
    db.refresh(item)

    return item


from app.schemas import AlertSettingResponse, AlertSettingUpdate
from app.services.alert_settings_service import (
    get_or_create_alert_settings,
    update_alert_settings,
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
