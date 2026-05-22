import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from app.models import (
    Alert,
    Competition,
    Event,
    MonitoredCompetition,
    MonitoredMarket,
    OddsSnapshot,
    Team,
)
from app.services.alert_engine import evaluate_alert
from app.services.alert_settings_service import get_or_create_alert_settings
from app.services.odds_api_io_provider import OddsApiIoProvider
from app.services.provider_bookmaker_settings_service import get_configured_bookmakers_csv
from app.services.telegram_notifier import send_telegram_alert_summary
from app.services.variation_engine import calculate_variation


def _parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    clean_value = str(value).replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(clean_value)
    except ValueError:
        return datetime.now(timezone.utc).replace(tzinfo=None)

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


DEFAULT_MONITORED_MARKETS = {
    "ML",
    "Totals",
    "Both Teams To Score",
    "Spread",
}




MARKET_PROVIDER_ALIASES = {
    "1X2": {"ML"},
    "Moneyline": {"ML"},
    "Vincente": {"ML"},

    "Over/Under": {"Totals"},
    "Over/Under 0.5": {"Totals"},
    "Over/Under 1.5": {"Totals"},
    "Over/Under 2.5": {"Totals"},
    "Over/Under 3.5": {"Totals"},
    "Over/Under 4.5": {"Totals"},

    "Goal/No Goal": {"Both Teams To Score"},
    "Gol/No Gol": {"Both Teams To Score"},
    "Both Teams To Score": {"Both Teams To Score"},

    "Handicap": {"Spread"},
    "Handicap principale": {"Spread"},
    "Handicap asiatico": {"Spread"},
    "Spread": {"Spread"},

    "Doppia chance": {"Double Chance"},
    "Double Chance": {"Double Chance"},

    "Draw No Bet": {"Draw No Bet"},
    "Rimborso pareggio": {"Draw No Bet"},

    "Handicap europeo": {"European Handicap"},
    "European Handicap": {"European Handicap"},

    "Corner Handicap": {"Corners Spread"},
    "Corner Over/Under": {"Corners Totals"},
    "Cartellini Over/Under": {"Bookings Totals"},
}


def _expand_market_aliases(market_names: set) -> set:
    expanded = set(market_names)

    for market_name in market_names:
        expanded.update(MARKET_PROVIDER_ALIASES.get(market_name, set()))

    return expanded

def _empty_ignored_odds_breakdown() -> Dict[str, int]:
    return {
        "inactive_competition": 0,
        "missing_provider_league_slug": 0,
        "inactive_market": 0,
        "unsupported_market": 0,
        "inactive_bookmaker": 0,
        "missing_previous_snapshot": 0,
        "unchanged_odds": 0,
        "invalid_odds": 0,
        "missing_event_mapping": 0,
        "below_alert_threshold": 0,
        "outside_alert_range": 0,
        "other": 0,
    }


def _empty_ignored_market_breakdown_by_name() -> Dict[str, Dict[str, int]]:
    return {
        "inactive_market": {},
        "unsupported_market": {},
    }


def _increment_ignored_market_name(
    breakdown: Dict[str, Dict[str, int]],
    reason: str,
    odd_data: Dict,
) -> None:
    if reason not in breakdown:
        return

    market_name = odd_data.get("market_name") or "Unknown market"
    line = odd_data.get("line")

    if line is not None:
        market_name = "{} {}".format(market_name, line)

    breakdown[reason][market_name] = breakdown[reason].get(market_name, 0) + 1


def _empty_ignored_events_breakdown() -> Dict[str, int]:
    return {
        "inactive_competition": 0,
        "missing_provider_league_slug": 0,
        "other": 0,
    }


def _get_active_monitored_market_names(db) -> set:
    market_names = {
        item.market_name
        for item in db.query(MonitoredMarket)
        .filter(MonitoredMarket.is_active.is_(True))
        .all()
    }

    if not market_names and db.query(MonitoredMarket).count() == 0:
        return DEFAULT_MONITORED_MARKETS

    return _expand_market_aliases(market_names)


def _get_configured_monitored_market_names(db) -> set:
    market_names = {
        item.market_name
        for item in db.query(MonitoredMarket).all()
    }

    return _expand_market_aliases(market_names)


def _is_monitored_market(odd_data: Dict, active_market_names: set) -> bool:
    market_name = odd_data.get("market_name") or ""

    if "HT" in market_name:
        return False

    if market_name.startswith("Team Total"):
        return False

    return market_name in active_market_names


def _ignored_market_reason(
    odd_data: Dict,
    active_market_names: set,
    configured_market_names: set,
) -> Optional[str]:
    market_name = odd_data.get("market_name") or ""

    if "HT" in market_name:
        return "unsupported_market"

    if market_name.startswith("Team Total"):
        return "unsupported_market"

    if market_name in active_market_names:
        return None

    if market_name in configured_market_names or market_name in DEFAULT_MONITORED_MARKETS:
        return "inactive_market"

    return "unsupported_market"


def _odds_value_is_valid(odd_data: Dict) -> bool:
    odds_decimal = odd_data.get("odds_decimal")

    try:
        return float(odds_decimal) > 0
    except (TypeError, ValueError):
        return False


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
    active_market_names = _get_active_monitored_market_names(db)
    configured_market_names = _get_configured_monitored_market_names(db)

    provider = OddsApiIoProvider(
        bookmakers_csv=get_configured_bookmakers_csv(db),
        usage_db=db,
    )
    sample = provider.get_sample(
        limit=limit,
        league_slugs=active_provider_league_slugs,
    )

    events_by_provider_id = {}
    ignored_events = 0
    ignored_events_breakdown = _empty_ignored_events_breakdown()
    ignored_odds_breakdown = _empty_ignored_odds_breakdown()
    ignored_market_breakdown_by_name = _empty_ignored_market_breakdown_by_name()

    for event_data in sample["events"]:
        if not _is_monitored_competition(event_data, active_competition_names):
            ignored_events += 1
            ignored_events_breakdown["inactive_competition"] += 1
            continue

        event = _get_or_create_event(db, event_data)
        events_by_provider_id[event_data["provider_event_id"]] = event

    alert_settings = get_or_create_alert_settings(db)

    inserted_snapshots = 0
    unchanged_snapshots = 0
    created_alerts = 0
    skipped_duplicate_alerts = 0
    notification_logs_created = 0
    created_alert_records = []

    captured_at = datetime.now(timezone.utc).replace(tzinfo=None)

    ignored_odds = 0

    for odd_data in sample["odds"]:
        ignored_market_reason = _ignored_market_reason(
            odd_data,
            active_market_names,
            configured_market_names,
        )
        if ignored_market_reason:
            ignored_odds += 1
            ignored_odds_breakdown[ignored_market_reason] += 1
            _increment_ignored_market_name(
                ignored_market_breakdown_by_name,
                ignored_market_reason,
                odd_data,
            )
            continue

        event = events_by_provider_id.get(odd_data["provider_event_id"])
        if not event:
            ignored_odds += 1
            ignored_odds_breakdown["missing_event_mapping"] += 1
            continue

        if not _odds_value_is_valid(odd_data):
            ignored_odds += 1
            ignored_odds_breakdown["invalid_odds"] += 1
            continue

        previous_snapshot = _find_previous_snapshot(db, event.id, odd_data)

        if previous_snapshot and previous_snapshot.odds_decimal == odd_data["odds_decimal"]:
            unchanged_snapshots += 1
            ignored_odds_breakdown["unchanged_odds"] += 1
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

                created_alert_records.append(alert)

                created_alerts += 1
            else:
                ignored_odds_breakdown["below_alert_threshold"] += 1
        else:
            ignored_odds_breakdown["missing_previous_snapshot"] += 1

    alert_records_to_notify = [
        alert
        for alert in created_alert_records
        if alert.direction == "decrease"
    ]

    if alert_records_to_notify:
        notification_result = send_telegram_alert_summary(
            db=db,
            alerts=alert_records_to_notify,
        )
        notification_logs_created += notification_result.get("logs_created", 0)

    db.commit()

    return {
        "provider": sample["provider"],
        "events_received": sample["events_count"],
        "events_ignored": ignored_events,
        "ignored_events_breakdown": ignored_events_breakdown,
        "active_competitions_count": len(active_competitions),
        "active_provider_league_slugs_count": len(active_provider_league_slugs),
        "odds_received": sample["odds_count"],
        "odds_ignored": ignored_odds,
        "ignored_odds_breakdown": ignored_odds_breakdown,
        "ignored_market_breakdown_by_name": ignored_market_breakdown_by_name,
        "active_markets_count": len(active_market_names),
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
