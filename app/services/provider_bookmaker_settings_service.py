import os
from datetime import datetime, timezone

from app.models import ProviderBookmakerSetting
from app.services.provider_plan_settings_service import get_or_create_provider_plan_settings


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_bookmakers_csv(value: str) -> str:
    bookmakers = []
    seen = set()

    for raw_item in str(value or "").split(","):
        bookmaker = raw_item.strip()

        if not bookmaker:
            continue

        key = bookmaker.lower()
        if key in seen:
            continue

        seen.add(key)
        bookmakers.append(bookmaker)

    return ",".join(bookmakers)


def bookmakers_from_csv(value: str) -> list:
    return [
        bookmaker.strip()
        for bookmaker in str(value or "").split(",")
        if bookmaker.strip()
    ]


def _default_bookmakers_csv() -> str:
    raw_value = (
        os.getenv("ODDS_API_IO_BOOKMAKERS")
        or os.getenv("ODDS_API_BOOKMAKERS")
        or "Stake,Sbobet"
    )

    return normalize_bookmakers_csv(raw_value)


def validate_provider_bookmaker_settings(db, bookmakers_csv: str):
    normalized = normalize_bookmakers_csv(bookmakers_csv)
    bookmakers = bookmakers_from_csv(normalized)

    if not bookmakers:
        raise ValueError("Inserisci almeno un bookmaker provider.")

    plan = get_or_create_provider_plan_settings(db)

    if len(bookmakers) > plan.max_bookmakers:
        raise ValueError(
            "Troppi bookmaker per il piano API {plan_name}: {current} configurati su massimo {limit}. "
            "Riduci i bookmaker oppure aggiorna il Piano API."
            .format(
                plan_name=plan.plan_name,
                current=len(bookmakers),
                limit=plan.max_bookmakers,
            )
        )

    return normalized


def get_or_create_provider_bookmaker_settings(db):
    item = db.query(ProviderBookmakerSetting).order_by(ProviderBookmakerSetting.id).first()

    if item:
        return item

    item = ProviderBookmakerSetting(
        bookmakers_csv=_default_bookmakers_csv(),
        created_at=_utc_now_naive(),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def get_configured_bookmakers_csv(db) -> str:
    return get_or_create_provider_bookmaker_settings(db).bookmakers_csv


def get_configured_bookmakers(db) -> list:
    return bookmakers_from_csv(get_configured_bookmakers_csv(db))


def update_provider_bookmaker_settings(db, bookmakers_csv: str):
    normalized = validate_provider_bookmaker_settings(
        db=db,
        bookmakers_csv=bookmakers_csv,
    )

    item = get_or_create_provider_bookmaker_settings(db)
    item.bookmakers_csv = normalized

    db.commit()
    db.refresh(item)

    return item
