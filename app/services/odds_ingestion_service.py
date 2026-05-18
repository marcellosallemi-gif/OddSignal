import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from app.models import Alert, Competition, Event, MonitoredCompetition, OddsSnapshot, Team
from app.services.alert_engine import evaluate_alert
from app.services.alert_settings_service import get_or_create_alert_settings
from app.services.odds_api_io_provider import OddsApiIoProvider
from app.services.telegram_notifier import send_telegram_alert
from app.services.variation_engine import calculate_variation


def _parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    clean_value = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(clean_value)

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed


def _get_alert_deduplication_minutes() -> int:
    raw_value = os.getenv("ALERT_DEDUPLICATION_MINUTES", "30")

    try:
        value = int(raw_value)
    except ValueError:
        return 30

    if value < 1:
        return 30

    return value


def _get_or_create_competition(
    db,
    name: str,
    provider_league_slug: str = None,
) -> Competition:
    competition = db.query(Competition).filter(Competition.name == name).first()
    if competition:
        if provider_league_slug and not competition.provider_league_slug:
            competition.provider_league_slug = provider_league_slug
            db.flush()
        return competition

    competition = Competition(
        name=name,
        country="Unknown",
        provider_league_slug=provider_league_slug,
    )
    db.add(competition)
    db.flush()
    return competition


def _get_or_create_team(db, name: str) -> Team:
    team = db.query(Team).filter(Team.name == name).first()
    if team:
        return team

    team = Team(name=name)
    db.add(team)
    db.flush()
    return team


def _get_or_create_event(db, event_data: Dict) -> Event:
    competition = _get_or_create_competition(
        db,
        event_data.get("league_name") or "Unknown competition",
        event_data.get("league_slug"),
    )
    home_team = _get_or_create_team(db, event_data.get("home_team") or "Unknown home")
    away_team = _get_or_create_team(db, event_data.get("away_team") or "Unknown away")
    start_time = _parse_datetime(event_data.get("event_date"))

    event = (
        db.query(Event)
        .filter(
            Event.competition_id == competition.id,
            Event.home_team_id == home_team.id,
            Event.away_team_id == away_team.id,
            Event.start_time == start_time,
        )
        .first()
    )
    if event:
        event.status = event_data.get("status") or event.status
        return event

    event = Event(
        competition_id=competition.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        start_time=start_time,
        status=event_data.get("status") or "pending",
    )
    db.add(event)
    db.flush()
    return event


def _market_key(odd_data: Dict) -> str:
    market_name = odd_data.get("market_name") or "Unknown market"
    line = odd_data.get("line")

    if line is None:
        return market_name

    return "{} {}".format(market_name, line)


def _is_monitored_market(odd_data: Dict) -> bool:
    market_name = odd_data.get("market_name") or ""

    if "HT" in market_name:
        return False

    if market_name.startswith("Team Total"):
        return False

    allowed_markets = {
        "ML",
        "Totals",
        "Both Teams To Score",
        "Spread",
    }

    return market_name in allowed_markets


def _get_active_monitored_competitions(db):
    return (
        db.query(MonitoredCompetition)
        .filter(MonitoredCompetition.is_active.is_(True))
        .all()
    )


def _get_active_monitored_competition_names(active_competitions) -> set:
    return {item.competition_name for item in active_competitions}


def _get_active_provider_league_slugs(active_competitions) -> list:
    return [
        item.provider_league_slug
        for item in active_competitions
        if item.provider_league_slug
    ]


def _is_monitored_competition(event_data: Dict, active_competitions: set) -> bool:
    league_name = event_data.get("league_name")
    return league_name in active_competitions


def _find_previous_snapshot(db, event_id: int, odd_data: Dict) -> Optional[OddsSnapshot]:
    return (
        db.query(OddsSnapshot)
        .filter(
            OddsSnapshot.event_id == event_id,
            OddsSnapshot.provider == odd_data["provider"],
            OddsSnapshot.bookmaker == odd_data["bookmaker"],
            OddsSnapshot.market == _market_key(odd_data),
            OddsSnapshot.selection == odd_data["selection"],
        )
        .order_by(OddsSnapshot.captured_at.desc(), OddsSnapshot.id.desc())
        .first()
    )


def _recent_alert_exists(
    db,
    event_id: int,
    odd_data: Dict,
    alert_result: Dict,
    captured_at: datetime,
) -> bool:
    deduplication_minutes = _get_alert_deduplication_minutes()
    cutoff = captured_at - timedelta(minutes=deduplication_minutes)

    existing_alert = (
        db.query(Alert)
        .filter(
            Alert.event_id == event_id,
            Alert.provider == odd_data["provider"],
            Alert.bookmaker == odd_data["bookmaker"],
            Alert.market == _market_key(odd_data),
            Alert.selection == odd_data["selection"],
            Alert.alert_type == alert_result["alert_type"],
            Alert.created_at >= cutoff,
        )
        .first()
    )

    return existing_alert is not None


def ingest_odds_sample(db, limit: int = 3) -> Dict:
    active_competitions = _get_active_monitored_competitions(db)
    active_competition_names = _get_active_monitored_competition_names(active_competitions)
    active_provider_league_slugs = _get_active_provider_league_slugs(active_competitions)

    provider = OddsApiIoProvider()
    sample = provider.get_sample(
        limit=limit,
        league_slugs=active_provider_league_slugs,
    )

    events_by_provider_id = {}
    ignored_events = 0

    for event_data in sample["events"]:
        if not _is_monitored_competition(event_data, active_competition_names):
            ignored_events += 1
            continue

        event = _get_or_create_event(db, event_data)
        events_by_provider_id[event_data["provider_event_id"]] = event

    alert_settings = get_or_create_alert_settings(db)

    inserted_snapshots = 0
    unchanged_snapshots = 0
    created_alerts = 0
    skipped_duplicate_alerts = 0
    notification_logs_created = 0

    captured_at = datetime.now(timezone.utc).replace(tzinfo=None)

    ignored_odds = 0

    for odd_data in sample["odds"]:
        if not _is_monitored_market(odd_data):
            ignored_odds += 1
            continue

        event = events_by_provider_id.get(odd_data["provider_event_id"])
        if not event:
            continue

        previous_snapshot = _find_previous_snapshot(db, event.id, odd_data)

        if previous_snapshot and previous_snapshot.odds_decimal == odd_data["odds_decimal"]:
            unchanged_snapshots += 1
            continue

        snapshot = OddsSnapshot(
            event_id=event.id,
            provider=odd_data["provider"],
            provider_event_id=odd_data.get("provider_event_id"),
            bookmaker=odd_data["bookmaker"],
            market=_market_key(odd_data),
            selection=odd_data["selection"],
            line=odd_data.get("line"),
            odds_decimal=odd_data["odds_decimal"],
            provider_updated_at=_parse_datetime(odd_data.get("updated_at")),
            captured_at=captured_at,
            raw_payload=json.dumps(odd_data.get("raw") or {}, ensure_ascii=False),
        )
        db.add(snapshot)
        inserted_snapshots += 1

        if previous_snapshot:
            variation = calculate_variation(
                previous_snapshot.odds_decimal,
                odd_data["odds_decimal"],
            )
            alert_result = evaluate_alert(
                variation,
                min_percent=alert_settings.min_percent,
                max_percent=alert_settings.max_percent,
                critical_percent=alert_settings.critical_percent,
            )

            if alert_result:
                if _recent_alert_exists(
                    db=db,
                    event_id=event.id,
                    odd_data=odd_data,
                    alert_result=alert_result,
                    captured_at=captured_at,
                ):
                    skipped_duplicate_alerts += 1
                    continue

                alert = Alert(
                    event_id=event.id,
                    provider=odd_data["provider"],
                    bookmaker=odd_data["bookmaker"],
                    market=_market_key(odd_data),
                    selection=odd_data["selection"],
                    previous_odds=variation["previous_odds"],
                    current_odds=variation["current_odds"],
                    variation_percent=variation["variation_percent"],
                    direction=variation["direction"],
                    alert_type=alert_result["alert_type"],
                    created_at=captured_at,
                )
                db.add(alert)
                db.flush()

                send_telegram_alert(db=db, alert=alert)

                created_alerts += 1
                notification_logs_created += 1

    db.commit()

    return {
        "provider": sample["provider"],
        "events_received": sample["events_count"],
        "events_ignored": ignored_events,
        "active_competitions_count": len(active_competitions),
        "active_provider_league_slugs_count": len(active_provider_league_slugs),
        "odds_received": sample["odds_count"],
        "odds_ignored": ignored_odds,
        "snapshots_inserted": inserted_snapshots,
        "snapshots_unchanged": unchanged_snapshots,
        "alerts_created": created_alerts,
        "duplicate_alerts_skipped": skipped_duplicate_alerts,
        "notification_logs_created": notification_logs_created,
        "alert_settings": {
            "min_percent": alert_settings.min_percent,
            "max_percent": alert_settings.max_percent,
            "critical_percent": alert_settings.critical_percent,
            "deduplication_minutes": alert_settings.deduplication_minutes,
        },
    }
