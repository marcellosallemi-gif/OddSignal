from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Event
from app.schemas import EventResponse


router = APIRouter()


@router.get("/events", response_model=List[EventResponse])
def get_events(db: Session = Depends(get_db)):
    events = (
        db.query(Event)
        .options(
            joinedload(Event.competition),
            joinedload(Event.home_team),
            joinedload(Event.away_team),
        )
        .order_by(Event.start_time)
        .all()
    )

    return [
        {
            "id": event.id,
            "sport": event.competition.sport,
            "competition": event.competition.name,
            "home_team": event.home_team.name,
            "away_team": event.away_team.name,
            "match": "{} vs {}".format(event.home_team.name, event.away_team.name),
            "start_time": event.start_time,
            "status": event.status,
        }
        for event in events
    ]
