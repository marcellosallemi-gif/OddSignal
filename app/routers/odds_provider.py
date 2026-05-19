from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.odds_api_io_provider import OddsApiIoProvider
from app.services.odds_ingestion_service import ingest_odds_sample


router = APIRouter(prefix="/api/odds-provider", tags=["odds-provider"])


@router.get("/events")
def get_provider_events(limit: int = Query(default=10, ge=1, le=50)):
    try:
        provider = OddsApiIoProvider()
        first_bookmaker = provider.bookmakers.split(",")[0].strip()
        return provider.get_events(limit=limit, bookmaker=first_bookmaker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/events/{event_id}/odds")
def get_provider_event_odds(event_id: int):
    try:
        provider = OddsApiIoProvider()
        return provider.get_event_odds(event_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sample")
def get_provider_sample(limit: int = Query(default=3, ge=1, le=10)):
    try:
        provider = OddsApiIoProvider()
        return provider.get_sample(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ingest-sample")
def ingest_provider_sample(
    limit: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    try:
        return ingest_odds_sample(db=db, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "provider_error",
                "message": (
                    "Controllo quote non completato. Verifica provider, "
                    "campionati attivi e disponibilita eventi."
                ),
            },
        ) from exc
