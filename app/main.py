import asyncio
import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager, suppress

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
from datetime import datetime
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
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
from app.services.telegram_notifier import sync_telegram_recipients_from_telegram


logger = logging.getLogger(__name__)
AUTH_ENABLED_VALUES = {"1", "true", "yes", "on"}
AUTH_EXEMPT_PATHS = {"/health", "/health/", "/login", "/login/"}
AUTH_EXEMPT_PREFIXES = ("/static/",)
SESSION_COOKIE_NAME = "oddsignal_session"
SESSION_COOKIE_MAX_AGE_SECONDS = 365 * 24 * 60 * 60
TELEGRAM_AUTO_SYNC_ENABLED_VALUES = {"1", "true", "yes", "on"}
DEFAULT_TELEGRAM_AUTO_SYNC_INTERVAL_SECONDS = 300
telegram_auto_sync_task = None


def is_auth_enabled():
    return os.getenv("APP_AUTH_ENABLED", "0").strip().lower() in AUTH_ENABLED_VALUES


def is_secure_cookie():
    return os.getenv("APP_ENV", "").strip().lower() == "production"


def is_auth_exempt_path(path):
    return path in AUTH_EXEMPT_PATHS or path.startswith(AUTH_EXEMPT_PREFIXES)


def get_session_secret():
    session_secret = os.getenv("APP_SESSION_SECRET")
    if session_secret:
        return session_secret

    password = os.getenv("APP_PASSWORD", "")
    if password:
        return "password-fallback:{}".format(password)

    return ""


def credentials_are_valid(username, password):
    expected_username = os.getenv("APP_USERNAME")
    expected_password = os.getenv("APP_PASSWORD")

    if not expected_username or not expected_password:
        return False

    username_matches = secrets.compare_digest(username, expected_username)
    password_matches = secrets.compare_digest(password, expected_password)
    return username_matches and password_matches


def create_session_token(username):
    payload = "{}:{}".format(username, int(time.time()))
    payload_token = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    payload_token = payload_token.rstrip("=")
    signature = hmac.new(
        get_session_secret().encode("utf-8"),
        payload_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return "{}.{}".format(payload_token, signature)


def session_token_is_valid(token):
    session_secret = get_session_secret()
    expected_username = os.getenv("APP_USERNAME", "")

    if not token or not session_secret or not expected_username or "." not in token:
        return False

    payload_token, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        session_secret.encode("utf-8"),
        payload_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not secrets.compare_digest(signature, expected_signature):
        return False

    padding = "=" * (-len(payload_token) % 4)
    try:
        decoded = base64.urlsafe_b64decode(
            (payload_token + padding).encode("ascii")
        ).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False

    username, separator, _created_at = decoded.partition(":")
    if not separator:
        return False

    return secrets.compare_digest(username, expected_username)


def request_has_valid_session(request):
    return session_token_is_valid(request.cookies.get(SESSION_COOKIE_NAME))


def set_session_cookie(response, username):
    response.set_cookie(
        SESSION_COOKIE_NAME,
        create_session_token(username),
        max_age=SESSION_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=is_secure_cookie(),
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response):
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def login_page(error_message=None, status_code=200):
    error_html = ""
    if error_message:
        error_html = '<p class="error">{}</p>'.format(error_message)

    html = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OddSignal - Login</title>
  <style>
    body {
      min-height: 100vh;
      margin: 0;
      display: grid;
      place-items: center;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5faf8;
      color: #0b2540;
    }
    main {
      width: min(420px, calc(100vw - 32px));
      background: #ffffff;
      border: 1px solid rgba(13, 31, 45, 0.12);
      border-radius: 18px;
      padding: 28px;
      box-shadow: 0 22px 60px rgba(13, 31, 45, 0.10);
    }
    img {
      display: block;
      width: 240px;
      max-width: 100%;
      height: auto;
      margin: 0 auto 24px;
    }
    label {
      display: grid;
      gap: 6px;
      margin-bottom: 14px;
      font-weight: 700;
    }
    input {
      padding: 11px 12px;
      border: 1px solid rgba(13, 31, 45, 0.18);
      border-radius: 10px;
      font: inherit;
    }
    button {
      width: 100%;
      margin-top: 8px;
      padding: 11px 14px;
      border: 0;
      border-radius: 10px;
      background: #1f9d69;
      color: #ffffff;
      font-weight: 800;
      cursor: pointer;
    }
    .error {
      margin: 0 0 14px;
      color: #b42318;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <main>
    <img src="/static/brand/oddsignal-horizontal.png" alt="OddSignal">
    __ERROR_HTML__
    <form method="post" action="/login">
      <label>
        Username
        <input name="username" autocomplete="username" required>
      </label>
      <label>
        Password
        <input name="password" type="password" autocomplete="current-password" required>
      </label>
      <button type="submit">Accedi</button>
    </form>
  </main>
</body>
</html>
"""
    return HTMLResponse(
        html.replace("__ERROR_HTML__", error_html),
        status_code=status_code,
    )


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


def is_telegram_auto_sync_enabled():
    return (
        os.getenv("TELEGRAM_AUTO_SYNC_ENABLED", "0").strip().lower()
        in TELEGRAM_AUTO_SYNC_ENABLED_VALUES
    )


def get_telegram_auto_sync_interval_seconds():
    raw_value = os.getenv(
        "TELEGRAM_AUTO_SYNC_INTERVAL_SECONDS",
        str(DEFAULT_TELEGRAM_AUTO_SYNC_INTERVAL_SECONDS),
    )
    try:
        interval = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_TELEGRAM_AUTO_SYNC_INTERVAL_SECONDS

    return interval if interval > 0 else DEFAULT_TELEGRAM_AUTO_SYNC_INTERVAL_SECONDS


def run_telegram_auto_sync_once():
    db = SessionLocal()
    try:
        result = sync_telegram_recipients_from_telegram(db)
    finally:
        db.close()

    if result["status"] == "skipped":
        logger.info(result["message"])
    elif result["status"] == "failed":
        logger.warning(result["message"])
    else:
        logger.info("Sync automatico Telegram completato: %s account.", result["synced_count"])

    return result


async def telegram_auto_sync_loop():
    while True:
        try:
            await asyncio.to_thread(run_telegram_auto_sync_once)
        except Exception:
            logger.exception("Sync automatico Telegram non completato.")

        await asyncio.sleep(get_telegram_auto_sync_interval_seconds())


async def start_telegram_auto_sync():
    global telegram_auto_sync_task

    if not is_telegram_auto_sync_enabled() or telegram_auto_sync_task is not None:
        return

    telegram_auto_sync_task = asyncio.create_task(telegram_auto_sync_loop())


async def stop_telegram_auto_sync():
    global telegram_auto_sync_task

    if telegram_auto_sync_task is None:
        return

    telegram_auto_sync_task.cancel()
    with suppress(asyncio.CancelledError):
        await telegram_auto_sync_task
    telegram_auto_sync_task = None


@asynccontextmanager
async def lifespan(app):
    load_environment()
    init_db()
    await odds_scheduler.start()
    await start_telegram_auto_sync()
    try:
        yield
    finally:
        await stop_telegram_auto_sync()
        await odds_scheduler.stop()


load_dotenv()

app = FastAPI(title="Football Odds Monitor", lifespan=lifespan)


@app.get("/login", response_class=HTMLResponse)
async def get_login():
    return login_page()


@app.post("/login")
async def post_login(request: Request):
    body = (await request.body()).decode("utf-8")
    form = parse_qs(body)
    username = form.get("username", [""])[0]
    password = form.get("password", [""])[0]

    if credentials_are_valid(username, password):
        response = RedirectResponse(url="/", status_code=303)
        set_session_cookie(response, username)
        return response

    return login_page("Credenziali non valide.", status_code=401)


@app.get("/logout")
@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response)
    return response


@app.middleware("http")
async def require_session_auth(request: Request, call_next):
    path = request.url.path

    if not is_auth_enabled():
        return await call_next(request)

    if is_auth_exempt_path(path):
        return await call_next(request)

    if request_has_valid_session(request):
        return await call_next(request)

    if request.method in {"GET", "HEAD"}:
        return RedirectResponse(url="/login", status_code=303)

    return Response(content="Autenticazione richiesta", status_code=401)


app.mount("/static", StaticFiles(directory="app/static"), name="static")


app.include_router(web_router)
app.include_router(health_router)
app.include_router(configuration_router)
app.include_router(events_router)
app.include_router(odds_router)
app.include_router(odds_provider_router)
app.include_router(alerts_router)
app.include_router(notification_logs_router)
app.include_router(system_router)
