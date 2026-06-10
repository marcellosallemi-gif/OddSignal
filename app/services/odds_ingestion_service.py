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
    sport: str = "football",
) -> Competition:
    competition = (
        db.query(Competition)
        .filter(
            Competition.name == name,
            Competition.sport == sport,
        )
        .first()
    )
    if competition:
        if provider_league_slug and not competition.provider_league_slug:
            competition.provider_league_slug = provider_league_slug
            db.flush()
        return competition

    competition = Competition(
        name=name,
        country="Unknown",
        sport=sport,
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
        event_data.get("sport") or "football",
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
    "Over/Under 0.5",
    "Over/Under 1.5",
    "Over/Under 2.5",
    "Over/Under 3.5",
    "Both Teams To Score",
    "Spread",
    "Draw No Bet",
    "Double Chance",
    "European Handicap",
}

SUPPORTED_TOTAL_LINES = {"0.5", "1.5", "2.5", "3.5"}
SUPPORTED_TOTAL_MARKETS = {
    "Over/Under {}".format(line)
    for line in SUPPORTED_TOTAL_LINES
}

SUPPORTED_PROVIDER_MARKETS = {
    "ML",
    "Moneyline",
    "Vincitore match",
    "Match Winner",
    "Totals",
    "Both Teams To Score",
    "Spread",
    "Draw No Bet",
    "Double Chance",
    "European Handicap",
}


MARKET_PROVIDER_ALIASES = {
    "1X2": {"ML"},
    "Moneyline": {"ML"},
    "Vincente": {"ML"},

    "Over/Under": {"Totals"},
    "Over/Under 0.5": {"Totals 0.5"},
    "Over/Under 1.5": {"Totals 1.5"},
    "Over/Under 2.5": {"Totals 2.5"},
    "Over/Under 3.5": {"Totals 3.5"},

    "Goal/No Goal": {"Both Teams To Score"},
    "Gol/No Gol": {"Both Teams To Score"},
    "Both Teams To Score": {"Both Teams To Score"},

    "Handicap": {"Spread"},
    "Handicap principale": {"Spread"},
    "Handicap asiatico": {"Spread"},
    "Asian Handicap": {"Spread"},
    "Spread": {"Spread"},

    "Doppia chance": {"Double Chance"},
    "Double Chance": {"Double Chance"},

    "Draw No Bet": {"Draw No Bet"},
    "Pareggio escluso": {"Draw No Bet"},
    "Rimborso pareggio": {"Draw No Bet"},

    "Handicap europeo": {"European Handicap"},
    "European Handicap": {"European Handicap"},

    "Corner Handicap": {"Corners Spread"},
    "Corner Over/Under": {"Corners Totals"},
    "Cartellini Over/Under": {"Bookings Totals"},
}


def _line_to_market_label(line) -> Optional[str]:
    if not _line_is_present(line):
        return None

    try:
        number = float(line)
    except (TypeError, ValueError):
        return str(line).strip()

    if number.is_integer():
        return str(int(number))

    return "{:g}".format(number)


def _line_label_is_number(line_label: Optional[str]) -> bool:
    if not line_label:
        return False

    try:
        float(line_label)
    except (TypeError, ValueError):
        return False

    return True


def normalize_provider_market(provider_market, line) -> Optional[str]:
    market_name = str(provider_market or "").strip()

    if market_name == "Totals":
        line_label = _line_to_market_label(line)
        if not line_label:
            return None
        return "Over/Under {}".format(line_label)

    if market_name.startswith("Totals "):
        line_label = _line_to_market_label(market_name.replace("Totals ", "", 1))
        if not _line_label_is_number(line_label):
            return market_name
        return "Over/Under {}".format(line_label)

    if market_name.startswith("Over/Under "):
        line_label = _line_to_market_label(
            market_name.replace("Over/Under ", "", 1)
        )
        if not line_label:
            return market_name
        return "Over/Under {}".format(line_label)

    return market_name


def _expand_market_aliases(market_names: set) -> set:
    expanded = set(market_names)

    for market_name in market_names:
        canonical_market = normalize_provider_market(market_name, None)
        if canonical_market:
            expanded.add(canonical_market)
            if canonical_market.startswith("Over/Under "):
                line = canonical_market.replace("Over/Under ", "", 1).strip()
                expanded.add("Totals {}".format(line))

        expanded.update(MARKET_PROVIDER_ALIASES.get(market_name, set()))

    return expanded


def _empty_ignored_odds_breakdown() -> Dict[str, int]:
    return {
        "inactive_competition": 0,
        "missing_provider_league_slug": 0,
        "inactive_market": 0,
        "disabled_market": 0,
        "unsupported_market": 0,
        "unsupported_line": 0,
        "inactive_bookmaker": 0,
        "missing_previous_snapshot": 0,
        "unchanged_odds": 0,
        "invalid_odds": 0,
        "invalid_market_selection": 0,
        "missing_event_mapping": 0,
        "below_alert_threshold": 0,
        "outside_alert_range": 0,
        "other": 0,
    }


def _empty_ignored_market_breakdown_by_name() -> Dict[str, Dict[str, int]]:
    return {
        "inactive_market": {},
        "disabled_market": {},
        "unsupported_market": {},
        "unsupported_line": {},
        "invalid_market_selection": {},
    }


def _increment_ignored_market_name(
    breakdown: Dict[str, Dict[str, int]],
    reason: str,
    odd_data: Dict,
) -> None:
    if reason not in breakdown:
        return

    market_name = _market_key(odd_data)
    canonical_market = normalize_provider_market(
        odd_data.get("market_name"),
        odd_data.get("line"),
    )
    if canonical_market and canonical_market != (odd_data.get("market_name") or ""):
        market_name = canonical_market

    breakdown[reason][market_name] = breakdown[reason].get(market_name, 0) + 1


def _empty_ignored_events_breakdown() -> Dict[str, int]:
    return {
        "inactive_competition": 0,
        "missing_provider_league_slug": 0,
        "other": 0,
    }


def _get_active_monitored_market_names(db, sport: str = "football"):
    configured_query = db.query(MonitoredMarket)

    if sport and hasattr(MonitoredMarket, "sport"):
        configured_query = configured_query.filter(MonitoredMarket.sport == sport)

    configured_markets = configured_query.all()

    active_market_names = {
        item.market_name
        for item in configured_markets
        if item.is_active
    }

    if active_market_names:
        expanded_market_names = set(active_market_names)

        if sport == "football":
            for canonical_name, aliases in MARKET_PROVIDER_ALIASES.items():
                if canonical_name in active_market_names or active_market_names.intersection(aliases):
                    expanded_market_names.add(canonical_name)
                    expanded_market_names.update(aliases)

        if sport == "tennis":
            if (
                "Vincitore match" in active_market_names
                or "ML" in active_market_names
                or "Moneyline" in active_market_names
                or "Match Winner" in active_market_names
            ):
                expanded_market_names.update({"Vincitore match", "ML", "Moneyline", "Match Winner"})

        return expanded_market_names

    # Compatibilità: se il database non ha ancora mercati configurati per il calcio,
    # usa i default storici così il calcio continua a funzionare.
    if not configured_markets and sport == "football":
        return set(DEFAULT_MONITORED_MARKETS)

    # Compatibilità limitata per test/database legacy:
    # se non esistono ancora mercati tennis configurati, accetta solo ML/Moneyline
    # eventualmente presente come vecchio mercato attivo globale.
    # In produzione, dopo la migration runtime, i mercati tennis esistono e questa
    # fallback non viene usata.
    if not configured_markets and sport == "tennis":
        legacy_active_markets = {
            item.market_name
            for item in db.query(MonitoredMarket)
            .filter(MonitoredMarket.is_active.is_(True))
            .all()
        }

        if legacy_active_markets.intersection({"ML", "Moneyline", "Vincitore match"}):
            return {"ML", "Moneyline", "Vincitore match"}

    return set()

def _get_configured_monitored_market_names(db) -> set:
    market_names = {
        item.market_name
        for item in db.query(MonitoredMarket).all()
    }

    return _expand_market_aliases(market_names)


def _is_monitored_market(odd_data: Dict, active_market_names: set) -> bool:
    market_name = odd_data.get("market_name") or ""

    if _is_unsupported_market_family(market_name):
        return False

    canonical_market = normalize_provider_market(market_name, odd_data.get("line"))
    return canonical_market in active_market_names


def _is_unsupported_market_family(market_name: str) -> bool:
    if "HT" in market_name:
        return True

    if market_name.startswith("Team Total"):
        return True

    if market_name.startswith("Corner"):
        return True

    if market_name.startswith("Booking"):
        return True

    if market_name.startswith("Card"):
        return True

    return False


def _has_specific_total_market(market_names: set) -> bool:
    for market_name in market_names:
        if market_name.startswith("Over/Under ") or market_name.startswith("Totals "):
            return True

    return False


def _is_total_line_supported(canonical_market: Optional[str], configured_market_names: set) -> bool:
    if not canonical_market or not canonical_market.startswith("Over/Under "):
        return True

    return (
        canonical_market in SUPPORTED_TOTAL_MARKETS
        or canonical_market in configured_market_names
    )


def _canonical_market_is_active(
    canonical_market: Optional[str],
    active_market_names: set,
    configured_market_names: set,
) -> bool:
    if not canonical_market:
        return False

    if canonical_market in active_market_names:
        return True

    if (
        canonical_market.startswith("Over/Under ")
        and "Totals" in active_market_names
        and not _has_specific_total_market(configured_market_names)
    ):
        return canonical_market in SUPPORTED_TOTAL_MARKETS

    return False


def _ignored_market_reason(
    odd_data: Dict,
    active_market_names: set,
    configured_market_names: set,
) -> Optional[str]:
    market_name = odd_data.get("market_name") or ""
    line = odd_data.get("line")

    if _is_unsupported_market_family(market_name):
        return "unsupported_market"

    if market_name not in SUPPORTED_PROVIDER_MARKETS:
        return "unsupported_market"

    canonical_market = normalize_provider_market(market_name, line)

    if market_name == "Totals" and not _line_is_present(line):
        return None

    if not _is_total_line_supported(canonical_market, configured_market_names):
        return "unsupported_line"

    if _canonical_market_is_active(
        canonical_market,
        active_market_names,
        configured_market_names,
    ):
        return None

    if (
        canonical_market in configured_market_names
        or canonical_market in DEFAULT_MONITORED_MARKETS
        or canonical_market in SUPPORTED_TOTAL_MARKETS
        or market_name in configured_market_names
        or market_name in DEFAULT_MONITORED_MARKETS
    ):
        if canonical_market and canonical_market.startswith("Over/Under "):
            return "disabled_market"
        return "inactive_market"

    return "unsupported_market"


def _odds_value_is_valid(odd_data: Dict) -> bool:
    odds_decimal = odd_data.get("odds_decimal")

    try:
        return float(odds_decimal) > 0
    except (TypeError, ValueError):
        return False


def _normalize_selection_value(value) -> str:
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


def _line_is_present(value) -> bool:
    return value is not None and str(value).strip() != ""


def _normalize_supported_odd_data(odd_data: Dict) -> Optional[Dict]:
    market_name = odd_data.get("market_name") or ""
    selection_key = _normalize_selection_value(odd_data.get("selection"))
    line = odd_data.get("line")
    normalized = dict(odd_data)

    ml_selections = {
        "home": "home",
        "1": "home",
        "draw": "draw",
        "x": "draw",
        "away": "away",
        "2": "away",
    }
    totals_selections = {
        "over": "Over",
        "under": "Under",
    }
    btts_selections = {
        "yes": "Goal",
        "goal": "Goal",
        "goals": "Goal",
        "no": "No Goal",
        "no goal": "No Goal",
        "nogoal": "No Goal",
    }
    double_chance_selections = {
        "1x": "1X",
        "home draw": "1X",
        "home or draw": "1X",
        "home_or_draw": "1X",
        "x2": "X2",
        "draw away": "X2",
        "draw or away": "X2",
        "draw_or_away": "X2",
        "12": "12",
        "home away": "12",
        "home or away": "12",
        "home_or_away": "12",
    }
    draw_no_bet_selections = {
        "home": "home",
        "1": "home",
        "away": "away",
        "2": "away",
    }

    if market_name in {"ML", "Moneyline", "Vincitore match", "Match Winner"}:
        if _line_is_present(line) or selection_key not in ml_selections:
            return None
        normalized["selection"] = ml_selections[selection_key]
        normalized["line"] = None
        normalized["market_name"] = "ML"
        return normalized

    if market_name == "Totals":
        if not _line_is_present(line) or selection_key not in totals_selections:
            return None
        normalized["selection"] = totals_selections[selection_key]
        return normalized

    if market_name == "Both Teams To Score":
        if _line_is_present(line) or selection_key not in btts_selections:
            return None
        normalized["selection"] = btts_selections[selection_key]
        normalized["line"] = None
        return normalized

    if market_name == "Double Chance":
        if _line_is_present(line) or selection_key not in double_chance_selections:
            return None
        normalized["selection"] = double_chance_selections[selection_key]
        normalized["line"] = None
        return normalized

    if market_name == "Draw No Bet":
        if _line_is_present(line) or selection_key not in draw_no_bet_selections:
            return None
        normalized["selection"] = draw_no_bet_selections[selection_key]
        normalized["line"] = None
        return normalized

    if market_name in {"Spread", "European Handicap"}:
        if not _line_is_present(line):
            return None
        return normalized

    return None


def _get_active_monitored_competitions(db, sport: str = None):
    query = db.query(MonitoredCompetition).filter(MonitoredCompetition.is_active.is_(True))

    if sport:
        query = query.filter(MonitoredCompetition.sport == sport)

    return query.all()


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


def _is_monitored_tennis_competition(event_data: Dict, active_provider_league_slugs: set) -> bool:
    league_slug = event_data.get("league_slug")
    return bool(league_slug and league_slug in active_provider_league_slugs)


def _sport_supports_market(sport: str, odd_data: Dict) -> bool:
    if sport != "tennis":
        return True

    market_name = odd_data.get("market_name") or ""
    line = odd_data.get("line")

    # Prima versione tennis: accetta solo vincitore match.
    # ML/Moneyline sono alias provider di Vincitore match.
    if market_name in {"ML", "Moneyline", "Vincitore match", "Match Winner"} and not _line_is_present(line):
        return True

    return False

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


def _event_display_name(event: Event) -> str:
    return "{} vs {}".format(event.home_team.name, event.away_team.name)


def _movement_decision(variation: Dict, alert_settings) -> str:
    absolute_variation_percent = variation["absolute_variation_percent"]

    if absolute_variation_percent < alert_settings.min_percent:
        return "below_threshold"

    if absolute_variation_percent <= alert_settings.max_percent:
        return "within_alert_range"

    if absolute_variation_percent > alert_settings.critical_percent:
        return "above_critical"

    return "above_critical"


def _track_top_movement(
    top_movements: list,
    sport: str,
    event: Event,
    odd_data: Dict,
    previous_odds: float,
    current_odds: float,
    variation_percent: float,
    decision: str,
) -> None:
    top_movements.append(
        {
            "sport": sport,
            "competition": event.competition.name,
            "event": _event_display_name(event),
            "market": _market_key(odd_data),
            "selection": odd_data["selection"],
            "bookmaker": odd_data.get("bookmaker"),
            "provider": odd_data.get("provider"),
            "previous_odds": previous_odds,
            "current_odds": current_odds,
            "variation_percent": variation_percent,
            "decision": decision,
        }
    )
    top_movements.sort(key=lambda item: abs(item["variation_percent"]), reverse=True)
    del top_movements[10:]


def _ingest_odds_sample_for_sport(db, limit: int = 3, sport: str = "football") -> Dict:
    active_competitions = _get_active_monitored_competitions(db, sport=sport)
    active_competition_names = _get_active_monitored_competition_names(active_competitions)
    active_provider_league_slugs = _get_active_provider_league_slugs(active_competitions)
    active_provider_league_slug_set = set(active_provider_league_slugs)
    active_market_names = _get_active_monitored_market_names(db, sport=sport)
    configured_market_names = _get_configured_monitored_market_names(db)

    provider = OddsApiIoProvider(
        bookmakers_csv=get_configured_bookmakers_csv(db),
        usage_db=db,
        sport=sport,
    )
    sample = provider.get_sample(
        limit=limit,
        league_slugs=active_provider_league_slugs,
    )

    events_by_provider_id = {}
    event_sports_by_provider_id = {}
    ignored_events = 0
    ignored_events_breakdown = _empty_ignored_events_breakdown()
    ignored_odds_breakdown = _empty_ignored_odds_breakdown()
    ignored_market_breakdown_by_name = _empty_ignored_market_breakdown_by_name()
    excluded_market_breakdown_by_name = _empty_ignored_market_breakdown_by_name()

    for event_data in sample["events"]:
        event_data["sport"] = event_data.get("sport") or sport
        if sport == "tennis":
            is_monitored_event = _is_monitored_tennis_competition(
                event_data,
                active_provider_league_slug_set,
            )
        else:
            is_monitored_event = _is_monitored_competition(
                event_data,
                active_competition_names,
            )

        if not is_monitored_event:
            ignored_events += 1
            ignored_events_breakdown["inactive_competition"] += 1
            continue

        event = _get_or_create_event(db, event_data)
        events_by_provider_id[event_data["provider_event_id"]] = event
        event_sports_by_provider_id[event_data["provider_event_id"]] = (
            event_data.get("sport") or sport
        )

    alert_settings = get_or_create_alert_settings(db)

    inserted_snapshots = 0
    unchanged_snapshots = 0
    created_alerts = 0
    skipped_duplicate_alerts = 0
    notification_logs_created = 0
    created_alert_records = []
    changed_odds_count = 0
    unchanged_odds_count = 0
    max_positive_variation_percent = None
    max_negative_variation_percent = None
    below_alert_threshold_count = 0
    within_alert_range_count = 0
    above_critical_threshold_count = 0
    top_movements = []

    captured_at = datetime.now(timezone.utc).replace(tzinfo=None)

    ignored_odds = 0
    processed_odds = 0
    excluded_odds = 0
    tennis_alerts_skipped = 0

    for odd_data in sample["odds"]:
        odd_sport = event_sports_by_provider_id.get(
            odd_data.get("provider_event_id"),
            sport,
        )
        if not _sport_supports_market(odd_sport, odd_data):
            ignored_odds += 1
            excluded_odds += 1
            ignored_odds_breakdown["unsupported_market"] += 1
            _increment_ignored_market_name(
                ignored_market_breakdown_by_name,
                "unsupported_market",
                odd_data,
            )
            _increment_ignored_market_name(
                excluded_market_breakdown_by_name,
                "unsupported_market",
                odd_data,
            )
            continue

        ignored_market_reason = _ignored_market_reason(
            odd_data,
            active_market_names,
            configured_market_names,
        )
        if ignored_market_reason:
            ignored_odds += 1
            excluded_odds += 1
            ignored_odds_breakdown[ignored_market_reason] += 1
            _increment_ignored_market_name(
                ignored_market_breakdown_by_name,
                ignored_market_reason,
                odd_data,
            )
            _increment_ignored_market_name(
                excluded_market_breakdown_by_name,
                ignored_market_reason,
                odd_data,
            )
            continue

        normalized_odd_data = _normalize_supported_odd_data(odd_data)
        if not normalized_odd_data:
            ignored_odds += 1
            excluded_odds += 1
            ignored_odds_breakdown["invalid_market_selection"] += 1
            _increment_ignored_market_name(
                ignored_market_breakdown_by_name,
                "invalid_market_selection",
                odd_data,
            )
            _increment_ignored_market_name(
                excluded_market_breakdown_by_name,
                "invalid_market_selection",
                odd_data,
            )
            continue
        odd_data = normalized_odd_data

        event = events_by_provider_id.get(odd_data["provider_event_id"])
        if not event:
            ignored_odds += 1
            ignored_odds_breakdown["missing_event_mapping"] += 1
            continue

        if not _odds_value_is_valid(odd_data):
            ignored_odds += 1
            ignored_odds_breakdown["invalid_odds"] += 1
            continue

        processed_odds += 1
        previous_snapshot = _find_previous_snapshot(db, event.id, odd_data)

        if previous_snapshot and previous_snapshot.odds_decimal == odd_data["odds_decimal"]:
            unchanged_snapshots += 1
            unchanged_odds_count += 1
            _track_top_movement(
                top_movements=top_movements,
                sport=odd_sport,
                event=event,
                odd_data=odd_data,
                previous_odds=previous_snapshot.odds_decimal,
                current_odds=odd_data["odds_decimal"],
                variation_percent=0,
                decision="unchanged",
            )
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
            changed_odds_count += 1
            variation = calculate_variation(
                previous_snapshot.odds_decimal,
                odd_data["odds_decimal"],
            )
            diagnostic_decision = _movement_decision(variation, alert_settings)

            if variation["variation_percent"] > 0:
                if (
                    max_positive_variation_percent is None
                    or variation["variation_percent"] > max_positive_variation_percent
                ):
                    max_positive_variation_percent = variation["variation_percent"]

            if variation["variation_percent"] < 0:
                if (
                    max_negative_variation_percent is None
                    or variation["variation_percent"] < max_negative_variation_percent
                ):
                    max_negative_variation_percent = variation["variation_percent"]

            if diagnostic_decision == "below_threshold":
                below_alert_threshold_count += 1
            elif diagnostic_decision == "within_alert_range":
                within_alert_range_count += 1
            elif diagnostic_decision == "above_critical":
                above_critical_threshold_count += 1

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
                    _track_top_movement(
                        top_movements=top_movements,
                        sport=odd_sport,
                        event=event,
                        odd_data=odd_data,
                        previous_odds=variation["previous_odds"],
                        current_odds=variation["current_odds"],
                        variation_percent=variation["variation_percent"],
                        decision="duplicate",
                    )
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
                _track_top_movement(
                    top_movements=top_movements,
                    sport=odd_sport,
                    event=event,
                    odd_data=odd_data,
                    previous_odds=variation["previous_odds"],
                    current_odds=variation["current_odds"],
                    variation_percent=variation["variation_percent"],
                    decision="alert_created",
                )
            else:
                ignored_odds_breakdown["below_alert_threshold"] += 1
                _track_top_movement(
                    top_movements=top_movements,
                    sport=odd_sport,
                    event=event,
                    odd_data=odd_data,
                    previous_odds=variation["previous_odds"],
                    current_odds=variation["current_odds"],
                    variation_percent=variation["variation_percent"],
                    decision=diagnostic_decision,
                )
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
    tennis_provider_diagnostics = None
    tennis_competition_configuration = None
    if sport == "tennis":
        tennis_provider_diagnostics = dict(getattr(provider, "last_diagnostics", {}) or {})
        tennis_competition_configuration = [
            {
                "competition_name": item.competition_name,
                "sport": item.sport,
                "provider_league_slug": item.provider_league_slug,
                "is_active": item.is_active,
            }
            for item in active_competitions
        ]

    return {
        "provider": sample["provider"],
        "sport": sport,
        "events_received": sample["events_count"],
        "events_ignored": ignored_events,
        "ignored_events_breakdown": ignored_events_breakdown,
        "active_competitions_count": len(active_competitions),
        "active_provider_league_slugs_count": len(active_provider_league_slugs),
        "odds_received": sample["odds_count"],
        "odds_ignored": ignored_odds,
        "odds_processed": processed_odds,
        "odds_excluded": excluded_odds,
        "ignored_odds_breakdown": ignored_odds_breakdown,
        "ignored_market_breakdown_by_name": ignored_market_breakdown_by_name,
        "excluded_market_breakdown_by_name": excluded_market_breakdown_by_name,
        "excluded_disabled_market": ignored_odds_breakdown["disabled_market"],
        "excluded_unsupported_line": ignored_odds_breakdown["unsupported_line"],
        "active_markets_count": len(active_market_names),
        "snapshots_inserted": inserted_snapshots,
        "snapshots_unchanged": unchanged_snapshots,
        "alerts_created": created_alerts,
        "duplicate_alerts_skipped": skipped_duplicate_alerts,
        "changed_odds_count": changed_odds_count,
        "unchanged_odds_count": unchanged_odds_count,
        "max_positive_variation_percent": max_positive_variation_percent,
        "max_negative_variation_percent": max_negative_variation_percent,
        "below_alert_threshold_count": below_alert_threshold_count,
        "within_alert_range_count": within_alert_range_count,
        "above_critical_threshold_count": above_critical_threshold_count,
        "top_movements": top_movements,
        "notification_logs_created": notification_logs_created,
        "tennis_alerts_skipped": tennis_alerts_skipped,
        "tennis_provider_diagnostics": tennis_provider_diagnostics,
        "tennis_competition_configuration": tennis_competition_configuration,
        "alert_settings": {
            "min_percent": alert_settings.min_percent,
            "max_percent": alert_settings.max_percent,
            "critical_percent": alert_settings.critical_percent,
            "deduplication_minutes": alert_settings.deduplication_minutes,
        },
    }


def _merge_counter_dicts(results, key):
    merged = {}

    for result in results:
        counter = result.get(key, {}) or {}

        if not isinstance(counter, dict):
            continue

        for item_key, value in counter.items():
            if isinstance(value, (int, float)):
                merged[item_key] = merged.get(item_key, 0) + value
                continue

            if isinstance(value, dict):
                nested = merged.setdefault(item_key, {})
                if not isinstance(nested, dict):
                    nested = {}
                    merged[item_key] = nested

                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, (int, float)):
                        nested[nested_key] = nested.get(nested_key, 0) + nested_value

    return merged


def _merge_top_movements(results):
    movements = []

    for result in results:
        movements.extend(result.get("top_movements", []) or [])

    movements.sort(key=lambda item: abs(item.get("variation_percent", 0)), reverse=True)
    return movements[:10]


def _max_optional_result_value(results, key):
    values = [
        result.get(key)
        for result in results
        if result.get(key) is not None
    ]

    if not values:
        return None

    return max(values)


def _min_optional_result_value(results, key):
    values = [
        result.get(key)
        for result in results
        if result.get(key) is not None
    ]

    if not values:
        return None

    return min(values)


def _merge_ingestion_results(results):
    if len(results) == 1:
        result = dict(results[0])
        result["sports_processed"] = [results[0]["sport"]]
        result["sport_results"] = results
        return result

    base = dict(results[0])
    numeric_keys = [
        "events_received",
        "events_ignored",
        "active_competitions_count",
        "active_provider_league_slugs_count",
        "odds_received",
        "odds_ignored",
        "odds_processed",
        "odds_excluded",
        "excluded_disabled_market",
        "excluded_unsupported_line",
        "snapshots_inserted",
        "snapshots_unchanged",
        "alerts_created",
        "duplicate_alerts_skipped",
        "changed_odds_count",
        "unchanged_odds_count",
        "below_alert_threshold_count",
        "within_alert_range_count",
        "above_critical_threshold_count",
        "notification_logs_created",
        "tennis_alerts_skipped",
    ]

    for key in numeric_keys:
        total = 0
        for result in results:
            value = result.get(key, 0)

            # Alcuni campi diagnostici possono essere dizionari nei risultati
            # dei singoli sport. L'aggregazione multi-sport deve sommare solo
            # valori numerici, altrimenti lo scheduler fallisce con int + dict.
            if isinstance(value, (int, float)):
                total += value

        base[key] = total

    base["sport"] = "multi"
    base["sports_processed"] = [result["sport"] for result in results]
    base["sport_results"] = results
    base["max_positive_variation_percent"] = _max_optional_result_value(
        results,
        "max_positive_variation_percent",
    )
    base["max_negative_variation_percent"] = _min_optional_result_value(
        results,
        "max_negative_variation_percent",
    )
    base["top_movements"] = _merge_top_movements(results)
    base["ignored_events_breakdown"] = _merge_counter_dicts(
        results,
        "ignored_events_breakdown",
    )
    base["ignored_odds_breakdown"] = _merge_counter_dicts(
        results,
        "ignored_odds_breakdown",
    )
    base["ignored_market_breakdown_by_name"] = _merge_counter_dicts(
        results,
        "ignored_market_breakdown_by_name",
    )
    base["excluded_market_breakdown_by_name"] = _merge_counter_dicts(
        results,
        "excluded_market_breakdown_by_name",
    )
    base["active_markets_count"] = max(
        result.get("active_markets_count", 0)
        for result in results
    )
    return base


def ingest_odds_sample(db, limit: int = 3) -> Dict:
    active_competitions = _get_active_monitored_competitions(db)
    active_sports = sorted(
        {
            item.sport or "football"
            for item in active_competitions
            if item.sport in {"football", "tennis"}
        }
    )

    if not active_sports:
        active_sports = ["football"]

    results = [
        _ingest_odds_sample_for_sport(db=db, limit=limit, sport=sport)
        for sport in active_sports
    ]
    return _merge_ingestion_results(results)
