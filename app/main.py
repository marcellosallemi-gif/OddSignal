from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI

from app.database import Base, SessionLocal, engine
from app.models import Competition, Event, OddsSnapshot, Team
from app.runtime import run_runtime_migrations, should_seed_demo_data
from app.routers.alerts import router as alerts_router
from app.routers.events import router as events_router
from app.routers.health import router as health_router
from app.routers.odds import router as odds_router
from app.routers.odds_provider import router as odds_provider_router
from app.routers.notification_logs import router as notification_logs_router
from app.services.mock_odds_provider import MockOddsProvider
from app.services.odds_scheduler import odds_scheduler


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
    init_db()
    await odds_scheduler.start()
    try:
        yield
    finally:
        await odds_scheduler.stop()


app = FastAPI(title="Football Odds Monitor", lifespan=lifespan)
app.include_router(health_router)
app.include_router(events_router)
app.include_router(odds_router)
app.include_router(odds_provider_router)
app.include_router(alerts_router)
app.include_router(notification_logs_router)
