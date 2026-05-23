from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.odds_api_io_provider import OddsApiIoProvider, classify_provider_error
from app.services.odds_ingestion_service import ingest_odds_sample
from app.services.provider_bookmaker_settings_service import get_configured_bookmakers_csv


router = APIRouter(prefix="/api/odds-provider", tags=["odds-provider"])


@router.get("/events")
def get_provider_events(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    try:
        provider = OddsApiIoProvider(
            bookmakers_csv=get_configured_bookmakers_csv(db),
            usage_db=db,
        )
        first_bookmaker = provider.bookmakers.split(",")[0].strip()
        return provider.get_events(limit=limit, bookmaker=first_bookmaker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/events/{event_id}/odds")
def get_provider_event_odds(
    event_id: int,
    db: Session = Depends(get_db),
):
    try:
        provider = OddsApiIoProvider(
            bookmakers_csv=get_configured_bookmakers_csv(db),
            usage_db=db,
        )
        return provider.get_event_odds(event_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sample")
def get_provider_sample(
    limit: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    try:
        provider = OddsApiIoProvider(
            bookmakers_csv=get_configured_bookmakers_csv(db),
            usage_db=db,
        )
        return provider.get_sample(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ingest-sample")
def ingest_provider_sample(
    limit: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    try:
        result = ingest_odds_sample(db=db, limit=limit)
        result["executed_at"] = datetime.now(timezone.utc).isoformat()
        return result
    except RuntimeError as exc:
        status_code, detail = classify_provider_error(exc)
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except Exception as exc:
        print("[manual-odds-ingest] error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Controllo quote non completato. Controlla i log Render.",
        ) from exc
