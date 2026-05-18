from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Alert, Event, NotificationLog


router = APIRouter()


@router.get("/notification-logs")
def get_notification_logs(
    channel: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = (
        db.query(NotificationLog)
        .options(
            joinedload(NotificationLog.alert),
            joinedload(NotificationLog.event).joinedload(Event.competition),
            joinedload(NotificationLog.event).joinedload(Event.home_team),
            joinedload(NotificationLog.event).joinedload(Event.away_team),
        )
    )

    if channel:
        query = query.filter(NotificationLog.channel == channel)

    if status:
        query = query.filter(NotificationLog.status == status)

    logs = (
        query
        .order_by(NotificationLog.sent_at.desc(), NotificationLog.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "alert_id": log.alert_id,
            "event": "{} vs {}".format(
                log.event.home_team.name,
                log.event.away_team.name,
            ),
            "competition": log.event.competition.name,
            "channel": log.channel,
            "status": log.status,
            "recipient": log.recipient,
            "message": log.message,
            "error_message": log.error_message,
            "sent_at": log.sent_at,
            "alert_type": log.alert.alert_type if log.alert else None,
            "bookmaker": log.alert.bookmaker if log.alert else None,
            "market": log.alert.market if log.alert else None,
            "selection": log.alert.selection if log.alert else None,
        }
        for log in logs
    ]
