import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx

from app.services.provider_usage_service import (
    activate_provider_rate_limit_cooldown,
    ensure_provider_request_allowed,
    record_provider_request,
)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


logger = logging.getLogger(__name__)


def load_local_env():
    if not os.path.exists(".env"):
        return

    with open(".env") as env_file:
        for line in env_file:
            clean_line = line.strip()
            if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
                continue

            key, value = clean_line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


class OddsApiIoProvider:
    missing_key_message = "ODDS_API_KEY is missing. Add it to your local .env file."

    def __init__(self, bookmakers_csv=None, usage_db=None, sport=None):
        if os.getenv("ODDS_API_SKIP_DOTENV") != "1":
            if load_dotenv is not None:
                load_dotenv()
            else:
                load_local_env()

        self.api_key = os.getenv("ODDS_API_IO_KEY") or os.getenv("ODDS_API_KEY")
        self.base_url = (
            os.getenv("ODDS_API_IO_BASE_URL")
            or os.getenv("ODDS_API_BASE_URL")
            or "https://api.odds-api.io/v3"
        )
        self.sport = sport or os.getenv("ODDS_API_IO_SPORT") or os.getenv("ODDS_API_SPORT") or "football"
        self.status = (
            os.getenv("ODDS_API_IO_STATUS")
            or os.getenv("ODDS_API_STATUS")
            or "pending"
        )
        self.bookmakers = (
            bookmakers_csv
            or os.getenv("ODDS_API_IO_BOOKMAKERS")
            or os.getenv("ODDS_API_BOOKMAKERS")
            or "Stake"
        )
        self.event_limit = (
            os.getenv("ODDS_API_IO_EVENT_LIMIT")
            or os.getenv("ODDS_API_EVENT_LIMIT")
            or "10"
        )
        self.leagues = os.getenv("ODDS_API_IO_LEAGUES") or os.getenv("ODDS_API_LEAGUES") or ""
        self.markets = os.getenv("ODDS_API_IO_MARKETS") or os.getenv("ODDS_API_MARKETS") or ""

        if not self.api_key or self.api_key == "PASTE_YOUR_API_KEY_HERE":
            raise RuntimeError(self.missing_key_message)

        self.base_url = self.base_url.rstrip("/")
        self.usage_db = usage_db
        self.last_response_status = None
        self.last_provider_error = None
        self.last_diagnostics = {}

    def masked_api_key(self):
        visible_prefix = self.api_key[:4] if len(self.api_key) > 4 else ""
        return "{}...hidden".format(visible_prefix)

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None):
        params = params or {}
        params.setdefault("apiKey", self.api_key)
        self.last_response_status = None
        self.last_provider_error = None

        url = "{}/{}".format(self.base_url, path.lstrip("/"))

        if self.usage_db is not None:
            ensure_provider_request_allowed(self.usage_db, path)

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, params=params)
        except httpx.TimeoutException as exc:
            self.last_provider_error = "timeout"
            if self.usage_db is not None:
                record_provider_request(self.usage_db, endpoint=path, status_code=None)
            raise RuntimeError("Odds-API.io timeout while calling {}".format(path)) from exc
        except httpx.RequestError as exc:
            self.last_provider_error = "request_error"
            if self.usage_db is not None:
                record_provider_request(self.usage_db, endpoint=path, status_code=None)
            raise RuntimeError("Odds-API.io request error while calling {}".format(path)) from exc

        self.last_response_status = response.status_code

        if self.usage_db is not None:
            record_provider_request(
                self.usage_db,
                endpoint=path,
                status_code=response.status_code,
            )

        if response.status_code == 401:
            self.last_provider_error = "unauthorized"
            raise RuntimeError("Odds-API.io API key is invalid or unauthorized.")
        if response.status_code == 429:
            self.last_provider_error = "rate_limit"
            if self.usage_db is not None:
                activate_provider_rate_limit_cooldown(
                    self.usage_db,
                    endpoint=path,
                )
            raise RuntimeError("Odds-API.io rate limit reached.")
        if response.status_code >= 400:
            self.last_provider_error = "http_error_{}".format(response.status_code)
            raise RuntimeError(
                "Odds-API.io HTTP error {}: {}".format(
                    response.status_code,
                    response.text[:500],
                )
            )

        return response.json()

    def build_bookmakers_url(self):
        return "{}/bookmakers".format(self.base_url)

    def build_events_url(
        self,
        league: Optional[str] = None,
        bookmaker: Optional[str] = None,
    ):
        params = {
            "apiKey": self.api_key,
            "sport": self.sport,
            "status": self.status,
            "limit": self.event_limit,
        }
        if league:
            params["league"] = league
        if bookmaker:
            params["bookmaker"] = bookmaker

        query = urlencode(params)
        return "{}/events?{}".format(self.base_url, query)

    def build_event_odds_url(self, event_id: Union[str, int]):
        query = urlencode(
            {
                "apiKey": self.api_key,
                "eventId": event_id,
                "bookmakers": self.bookmakers,
            }
        )
        return "{}/odds?{}".format(self.base_url, query)

    def build_multi_odds_url(self, event_ids: List[Union[str, int]]):
        query = urlencode(
            {
                "apiKey": self.api_key,
                "eventIds": ",".join([str(event_id) for event_id in event_ids]),
                "bookmakers": self.bookmakers,
            }
        )
        return "{}/odds/multi?{}".format(self.base_url, query)

    def get_leagues(self):
        return self._get(
            "/leagues",
            params={
                "sport": self.sport,
            },
        )

    def get_events(
        self,
        limit: Optional[int] = None,
        bookmaker: Optional[str] = None,
        league: Optional[str] = None,
    ):
        params = {
            "sport": self.sport,
            "status": self.status,
            "limit": str(limit or self.event_limit),
            "from": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        if bookmaker:
            params["bookmaker"] = bookmaker

        if league:
            params["league"] = league

        return self._get("/events", params=params)

    def get_event_odds(self, event_id: Union[str, int]):
        return self._get(
            "/odds",
            params={
                "eventId": event_id,
                "bookmakers": self.bookmakers,
            },
        )

    def get_sample(
        self,
        limit: Optional[int] = None,
        league_slugs: Optional[List[str]] = None,
    ):
        first_bookmaker = self.bookmakers.split(",")[0].strip()

        events = []
        self.last_diagnostics = {
            "sport": self.sport,
            "endpoint": "/events",
            "requested_leagues": league_slugs or [],
            "league_results": [],
            "empty_leagues_count": 0,
            "errored_leagues_count": 0,
        }
        if league_slugs:
            for league_slug in league_slugs:
                try:
                    league_events = self.get_events(
                        limit=limit,
                        bookmaker=first_bookmaker,
                        league=league_slug,
                    )
                except RuntimeError as exc:
                    self.last_diagnostics["errored_leagues_count"] += 1
                    self.last_diagnostics["league_results"].append(
                        {
                            "league_slug": league_slug,
                            "status": "error",
                            "events_count": 0,
                            "error_message": str(exc),
                        }
                    )
                    logger.info(
                        "Odds-API.io events diagnostics: sport=%s endpoint=%s "
                        "league=%s status=%s events_count=%s error=%s",
                        self.sport,
                        "/events",
                        league_slug,
                        "error",
                        0,
                        str(exc),
                    )
                    if self.sport != "tennis":
                        raise
                    continue

                events.extend(league_events)
                if not league_events:
                    self.last_diagnostics["empty_leagues_count"] += 1

                self.last_diagnostics["league_results"].append(
                    {
                        "league_slug": league_slug,
                        "status": "ok",
                        "events_count": len(league_events),
                    }
                )
                logger.info(
                    "Odds-API.io events diagnostics: sport=%s endpoint=%s "
                    "league=%s status=%s events_count=%s",
                    self.sport,
                    "/events",
                    league_slug,
                    "ok",
                    len(league_events),
                )
        else:
            events = self.get_events(limit=limit, bookmaker=first_bookmaker)

        normalized_events = [self.normalize_event(event) for event in events]
        odds = []

        for event in events:
            raw_odds = self.get_event_odds(event["id"])
            odds.extend(self.normalize_odds(raw_odds))

        return {
            "provider": "odds_api_io",
            "sport": self.sport,
            "bookmakers": [
                bookmaker.strip()
                for bookmaker in self.bookmakers.split(",")
                if bookmaker.strip()
            ],
            "league_slugs": league_slugs or [],
            "events_count": len(normalized_events),
            "odds_count": len(odds),
            "events": normalized_events,
            "odds": odds,
        }

    def normalize_event(self, event: Dict[str, Any]):
        league = event.get("league") or {}
        sport = event.get("sport") or {}

        return {
            "provider": "odds_api_io",
            "provider_event_id": str(event.get("id")),
            "sport": sport.get("slug"),
            "sport_name": sport.get("name"),
            "league_name": league.get("name"),
            "league_slug": league.get("slug"),
            "home_team": event.get("home"),
            "away_team": event.get("away"),
            "event_date": event.get("date"),
            "status": event.get("status"),
            "raw": event,
        }

    def normalize_odds(self, event_odds: Dict[str, Any]):
        normalized = []
        bookmakers = event_odds.get("bookmakers") or {}

        for bookmaker_name, markets in bookmakers.items():
            for market in markets:
                market_name = market.get("name")
                updated_at = market.get("updatedAt")
                odds_rows = market.get("odds") or []

                for row in odds_rows:
                    normalized.extend(
                        self._normalize_market_row(
                            event_odds=event_odds,
                            bookmaker_name=bookmaker_name,
                            market_name=market_name,
                            updated_at=updated_at,
                            row=row,
                        )
                    )

        return normalized

    def _normalize_market_row(
        self,
        event_odds: Dict[str, Any],
        bookmaker_name: str,
        market_name: str,
        updated_at: Optional[str],
        row: Dict[str, Any],
    ):
        ignored_keys = {"hdp"}
        line = row.get("hdp")
        normalized = []

        for selection, odd in row.items():
            if selection in ignored_keys:
                continue

            try:
                odds_decimal = float(odd)
            except (TypeError, ValueError):
                continue

            normalized.append(
                {
                    "provider": "odds_api_io",
                    "provider_event_id": str(event_odds.get("id")),
                    "event": "{} vs {}".format(
                        event_odds.get("home"),
                        event_odds.get("away"),
                    ),
                    "league_name": (event_odds.get("league") or {}).get("name"),
                    "bookmaker": bookmaker_name,
                    "market_name": market_name,
                    "selection": selection,
                    "line": line,
                    "odds_decimal": odds_decimal,
                    "updated_at": updated_at,
                    "raw": row,
                }
            )

        return normalized



def classify_provider_error(exc: RuntimeError):
    message = str(exc)

    if "Provider API cooldown active" in message:
        return 429, {
            "error": "provider_rate_limit_cooldown",
            "message": "Provider Odds-API.io in cooldown locale per rate limit. Attendi il reset prima di nuove chiamate.",
            "provider_message": message,
        }

    if "Provider API local hourly limit reached" in message:
        return 429, {
            "error": "provider_local_rate_limit",
            "message": "Limite locale richieste/ora raggiunto. Attendi il reset orario oppure aggiorna il Piano API.",
            "provider_message": message,
        }
    normalized = message.lower()

    if "rate limit" in normalized:
        return 429, {
            "error": "provider_rate_limit",
            "message": (
                "Rate limit Odds-API.io raggiunto. Attendi il reset del limite orario "
                "oppure riduci frequenza scheduler, eventi per ciclo o chiamate manuali."
            ),
            "provider_message": message,
        }

    if "api key" in normalized and ("missing" in normalized or "invalid" in normalized or "unauthorized" in normalized):
        return 401, {
            "error": "provider_auth_error",
            "message": "API key Odds-API.io mancante, non valida o non autorizzata.",
            "provider_message": message,
        }

    if "timeout" in normalized:
        return 504, {
            "error": "provider_timeout",
            "message": "Timeout durante la chiamata a Odds-API.io. Riprova più tardi.",
            "provider_message": message,
        }

    if "request error" in normalized:
        return 502, {
            "error": "provider_network_error",
            "message": "Errore di rete durante la chiamata a Odds-API.io.",
            "provider_message": message,
        }

    if "league not found" in normalized or "http error 404" in normalized:
        return 404, {
            "error": "provider_league_not_found",
            "message": "Campionato non trovato dal provider. Verifica provider_league_slug o disponibilità eventi.",
            "provider_message": message,
        }

    return 502, {
        "error": "provider_error",
        "message": "Errore provider Odds-API.io non classificato.",
        "provider_message": message,
    }
