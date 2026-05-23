from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Alert, Event, NotificationLog
from app.schemas import AlertResponse


router = APIRouter()


@router.get("/alerts", response_model=List[AlertResponse])
def get_alerts(
    provider: Optional[str] = Query(default=None),
    bookmaker: Optional[str] = Query(default=None),
    alert_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Alert)
        .options(
            joinedload(Alert.event).joinedload(Event.competition),
            joinedload(Alert.event).joinedload(Event.home_team),
            joinedload(Alert.event).joinedload(Event.away_team),
        )
    )

    if provider:
        query = query.filter(Alert.provider == provider)

    if bookmaker:
        query = query.filter(Alert.bookmaker == bookmaker)

    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)

    alerts = (
        query
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": alert.id,
            "event": "{} vs {}".format(
                alert.event.home_team.name,
                alert.event.away_team.name,
            ),
            "competition": alert.event.competition.name,
            "provider": alert.provider,
            "bookmaker": alert.bookmaker,
            "market": alert.market,
            "selection": alert.selection,
            "previous_odds": alert.previous_odds,
            "current_odds": alert.current_odds,
            "variation_percent": alert.variation_percent,
            "direction": alert.direction,
            "alert_type": alert.alert_type,
            "created_at": alert.created_at,
        }
        for alert in alerts
    ]


@router.delete("/alerts/recent")
def delete_recent_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 100))

    alerts_to_delete = (
        db.query(Alert)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(safe_limit)
        .all()
    )

    alert_ids = [alert.id for alert in alerts_to_delete]
    deleted_count = len(alert_ids)

    try:
        deleted_notification_logs = 0
        if alert_ids:
            deleted_notification_logs = (
                db.query(NotificationLog)
                .filter(NotificationLog.alert_id.in_(alert_ids))
                .delete(synchronize_session=False)
            )

        for alert in alerts_to_delete:
            db.delete(alert)

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Alert recenti non cancellati: errore durante la cancellazione dei log collegati.",
        ) from exc

    return {
        "deleted_count": deleted_count,
        "deleted_notification_logs": deleted_notification_logs,
        "message": "Alert recenti cancellati.",
    }
