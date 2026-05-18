from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Event, OddsSnapshot
from app.schemas import OddsResponse


router = APIRouter()


@router.get("/odds", response_model=List[OddsResponse])
def get_odds(
    provider: Optional[str] = Query(default=None),
    bookmaker: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = (
        db.query(OddsSnapshot)
        .options(
            joinedload(OddsSnapshot.event).joinedload(Event.competition),
            joinedload(OddsSnapshot.event).joinedload(Event.home_team),
            joinedload(OddsSnapshot.event).joinedload(Event.away_team),
        )
    )

    if provider:
        query = query.filter(OddsSnapshot.provider == provider)

    if bookmaker:
        query = query.filter(OddsSnapshot.bookmaker == bookmaker)

    odds_snapshots = (
        query
        .order_by(OddsSnapshot.captured_at.desc(), OddsSnapshot.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": snapshot.id,
            "event": "{} vs {}".format(
                snapshot.event.home_team.name,
                snapshot.event.away_team.name,
            ),
            "competition": snapshot.event.competition.name,
            "provider": snapshot.provider,
            "bookmaker": snapshot.bookmaker,
            "market": snapshot.market,
            "selection": snapshot.selection,
            "odds_decimal": snapshot.odds_decimal,
            "captured_at": snapshot.captured_at,
        }
        for snapshot in odds_snapshots
    ]
