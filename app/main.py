import base64
import binascii
import os
import secrets

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.database import Base, SessionLocal, engine
from app.models import Competition, Event, OddsSnapshot, Team
from app.runtime import load_environment, run_runtime_migrations, should_seed_demo_data
from app.routers.alerts import router as alerts_router
from app.routers.configuration import router as configuration_router
from app.routers.events import router as events_router
from app.routers.health import router as health_router
from app.routers.odds import router as odds_router
from app.routers.odds_provider import router as odds_provider_router
from app.routers.notification_logs import router as notification_logs_router
from app.routers.system import router as system_router
from app.routers.web import router as web_router
from app.services.mock_odds_provider import MockOddsProvider
from app.services.odds_scheduler import odds_scheduler


def is_auth_exempt_path(path):
    return path == "/health" or path == "/static" or path.startswith("/static/")


def unauthorized_response():
    return Response(
        content="Authentication required",
        status_code=401,
        headers={"WWW-Authenticate": "Basic"},
    )


def decode_basic_credentials(authorization):
    if not authorization:
        return None, None

    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "basic" or not credentials:
        return None, None

    try:
        decoded = base64.b64decode(credentials).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None, None

    username, separator, password = decoded.partition(":")
    if not separator:
        return None, None

    return username, password


def credentials_are_valid(username, password):
    expected_username = os.getenv("APP_USERNAME")
    expected_password = os.getenv("APP_PASSWORD")

    if not expected_username or not expected_password:
        return False

    username_matches = secrets.compare_digest(username, expected_username)
    password_matches = secrets.compare_digest(password, expected_password)
    return username_matches and password_matches


def get_or_create_competition(db, name, country):
    competition = db.query(Competition).filter(Competition.name == name).first()
    if competition:
        return competition

    competition = Competition(name=name, country=country)
    db.add(competition)
    db.flush()
    return competition


def get_or_create_team(db, name):
    team = db.query(Team).filter(Team.name == name).first()
    if team:
        return team

    team = Team(name=name)
    db.add(team)
    db.flush()
    return team


def seed_initial_data():
    db = SessionLocal()
    try:
        competitions = {
            "Serie A": get_or_create_competition(db, "Serie A", "Italy"),
            "Premier League": get_or_create_competition(
                db,
                "Premier League",
                "England",
            ),
            "Champions League": get_or_create_competition(
                db,
                "Champions League",
                "Europe",
            ),
        }
        teams = {
            name: get_or_create_team(db, name)
            for name in [
                "Inter",
                "Milan",
                "Juventus",
                "Roma",
                "Arsenal",
                "Chelsea",
            ]
        }

        seed_events = [
            (
                competitions["Serie A"],
                teams["Inter"],
                teams["Milan"],
                datetime(2026, 8, 15, 18, 30),
                "scheduled",
            ),
            (
                competitions["Premier League"],
                teams["Arsenal"],
                teams["Chelsea"],
                datetime(2026, 8, 16, 16, 0),
                "scheduled",
            ),
            (
                competitions["Champions League"],
                teams["Juventus"],
                teams["Roma"],
                datetime(2026, 9, 1, 20, 45),
                "scheduled",
            ),
        ]

        for competition, home_team, away_team, start_time, status in seed_events:
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
                continue

            db.add(
                Event(
                    competition_id=competition.id,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    start_time=start_time,
                    status=status,
                )
            )

        db.commit()
        seed_mock_odds(db)
        db.commit()
    finally:
        db.close()


def seed_mock_odds(db):
    events = db.query(Event).order_by(Event.id).all()
    provider = MockOddsProvider()

    for odds_data in provider.get_odds(events):
        odds_snapshot = (
            db.query(OddsSnapshot)
            .filter(
                OddsSnapshot.event_id == odds_data["event_id"],
                OddsSnapshot.provider == odds_data["provider"],
                OddsSnapshot.bookmaker == odds_data["bookmaker"],
                OddsSnapshot.market == odds_data["market"],
                OddsSnapshot.selection == odds_data["selection"],
            )
            .first()
        )
        if odds_snapshot:
            continue

        db.add(OddsSnapshot(**odds_data))


def init_db():
    Base.metadata.create_all(bind=engine)
    run_runtime_migrations()

    if should_seed_demo_data():
        seed_initial_data()


@asynccontextmanager
async def lifespan(app):
    load_environment()
    init_db()
    await odds_scheduler.start()
    try:
        yield
    finally:
        await odds_scheduler.stop()


load_dotenv()

app = FastAPI(title="Football Odds Monitor", lifespan=lifespan)


@app.middleware("http")
async def require_basic_auth(request: Request, call_next):
    if is_auth_exempt_path(request.url.path):
        return await call_next(request)

    username, password = decode_basic_credentials(
        request.headers.get("Authorization")
    )
    if username is None or not credentials_are_valid(username, password):
        return unauthorized_response()

    return await call_next(request)


app.mount("/static", StaticFiles(directory="app/static"), name="static")


AUTH_ENABLED_VALUES = {"1", "true", "yes", "on"}
AUTH_EXEMPT_PATHS = {"/health", "/health/", "/auth-debug"}
AUTH_EXEMPT_PREFIXES = ("/static/",)


def is_auth_enabled() -> bool:
    return os.getenv("APP_AUTH_ENABLED", "0").strip().lower() in AUTH_ENABLED_VALUES


def unauthorized_response() -> Response:
    return Response(
        content="Autenticazione richiesta",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="OddSignal"'},
    )


def valid_basic_auth_header(authorization) -> bool:
    expected_username = os.getenv("APP_USERNAME", "")
    expected_password = os.getenv("APP_PASSWORD", "")

    if not expected_username or not expected_password:
        return False

    if not authorization or not authorization.startswith("Basic "):
        return False

    token = authorization.removeprefix("Basic ").strip()

    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False

    if ":" not in decoded:
        return False

    username, password = decoded.split(":", 1)

    return (
        secrets.compare_digest(username, expected_username)
        and secrets.compare_digest(password, expected_password)
    )


@app.middleware("http")
async def require_dashboard_auth(request: Request, call_next):
    path = request.url.path

    if not is_auth_enabled():
        return await call_next(request)

    if path in AUTH_EXEMPT_PATHS or path.startswith(AUTH_EXEMPT_PREFIXES):
        return await call_next(request)

    if not valid_basic_auth_header(request.headers.get("authorization")):
        return unauthorized_response()

    return await call_next(request)
app.include_router(web_router)
app.include_router(health_router)
app.include_router(configuration_router)
app.include_router(events_router)
app.include_router(odds_router)
app.include_router(odds_provider_router)
app.include_router(alerts_router)
app.include_router(notification_logs_router)
app.include_router(system_router)


@app.get("/auth-debug")
def auth_debug():
    username = os.getenv("APP_USERNAME", "")
    password = os.getenv("APP_PASSWORD", "")
    return {
        "auth_enabled": os.getenv("APP_AUTH_ENABLED", ""),
        "username": username,
        "username_length": len(username),
        "password_present": bool(password),
        "password_length": len(password),
    }
