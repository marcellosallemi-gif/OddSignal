import asyncio
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app
from app.models import SchedulerSetting
from app.services.odds_scheduler import OddsScheduler
from app.services.scheduler_settings_service import get_or_create_scheduler_settings


class FakeSettings:
    def __init__(self, enabled, poll_interval_seconds, event_limit):
        self.enabled = enabled
        self.poll_interval_seconds = poll_interval_seconds
        self.event_limit = event_limit


class FakeDb:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_scheduler_cycle_reads_db_and_skips_polling_when_disabled(monkeypatch):
    from app.services import odds_scheduler as scheduler_module

    fake_db = FakeDb()
    settings = FakeSettings(
        enabled=False,
        poll_interval_seconds=3,
        event_limit=2,
    )

    monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(
        scheduler_module,
        "get_or_create_scheduler_settings",
        lambda db: settings,
    )

    def fail_ingestion(db, limit):
        raise AssertionError("Il polling quote non deve partire se enabled=false.")

    monkeypatch.setattr(scheduler_module, "ingest_odds_sample", fail_ingestion)

    interval_seconds = OddsScheduler()._run_configured_cycle()

    assert interval_seconds == 3
    assert fake_db.closed is True


def test_scheduler_notify_settings_changed_wakes_server_loop(monkeypatch):
    scheduler = OddsScheduler()
    cycles = []

    def fake_cycle():
        cycles.append(True)
        return 60

    monkeypatch.setattr(scheduler, "_run_configured_cycle", fake_cycle)

    async def run_scheduler():
        await scheduler.start(configured_enabled=True)
        await asyncio.sleep(0.05)
        scheduler.notify_settings_changed()
        await asyncio.sleep(0.05)
        assert scheduler.is_running() is True
        await scheduler.stop()

    asyncio.run(run_scheduler())

    assert len(cycles) >= 2


def test_scheduler_start_skips_loop_when_db_setting_disabled(monkeypatch):
    scheduler = OddsScheduler()

    def fake_load_configured_enabled():
        return False

    monkeypatch.setattr(
        scheduler,
        "_load_configured_enabled",
        fake_load_configured_enabled,
    )

    async def run_scheduler():
        await scheduler.start()
        assert scheduler.is_running() is False

    asyncio.run(run_scheduler())


def test_scheduler_start_loads_db_setting_and_starts_when_enabled(monkeypatch):
    scheduler = OddsScheduler()
    cycles = []

    def fake_load_configured_enabled():
        return True

    def fake_cycle():
        cycles.append(True)
        return 60

    monkeypatch.setattr(
        scheduler,
        "_load_configured_enabled",
        fake_load_configured_enabled,
    )
    monkeypatch.setattr(scheduler, "_run_configured_cycle", fake_cycle)

    async def run_scheduler():
        await scheduler.start()
        await asyncio.sleep(0.05)
        assert scheduler.is_running() is True
        await scheduler.stop()

    asyncio.run(run_scheduler())

    assert len(cycles) >= 1


def test_scheduler_runtime_status_endpoint_returns_runtime_fields():
    with TestClient(app) as client:
        response = client.get("/configuration/scheduler-runtime-status")

    assert response.status_code == 200
    data = response.json()
    assert "configured_enabled" in data
    assert "runtime_running" in data
    assert "last_started_at" in data
    assert "last_tick_at" in data
    assert "last_success_at" in data
    assert "last_error" in data


def test_odds_scheduler_enabled_env_does_not_override_existing_db_setting(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("ODDS_SCHEDULER_ENABLED", "1")
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "scheduler_settings.db"),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    db = TestingSessionLocal()

    try:
        db.add(
            SchedulerSetting(
                enabled=False,
                poll_interval_seconds=300,
                event_limit=1,
                created_at=datetime(2026, 1, 1, 0, 0, 0),
            )
        )
        db.commit()

        settings = get_or_create_scheduler_settings(db)

        assert settings.enabled is False
        assert db.query(SchedulerSetting).count() == 1
    finally:
        db.close()
