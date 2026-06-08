from datetime import datetime

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app
from app.models import ProviderApiRequestLog, ProviderPlanSetting
from app.services.provider_plan_settings_service import (
    get_or_create_provider_plan_settings,
    validate_scheduler_against_provider_plan,
)
from app.services.provider_usage_service import get_provider_usage_status


def make_usage_test_db(tmp_path):
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "provider_usage.db"),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    return TestingSessionLocal()


def test_get_system_status_returns_operational_summary():
    with TestClient(app) as client:
        response = client.get("/system/status")

    assert response.status_code == 200

    payload = response.json()

    assert "provider" in payload
    assert "sports" in payload
    assert "sport" in payload
    assert "bookmakers" in payload
    assert "scheduler" in payload
    assert "alerts" in payload
    assert "telegram" in payload
    assert "database_counts" in payload

    assert "enabled" in payload["scheduler"]
    assert "loop_running" in payload["scheduler"]
    assert "football" in payload["sports"]
    assert "tennis" in payload["sports"]
    assert "configured" in payload["telegram"]
    assert "events" in payload["database_counts"]
    assert "odds_snapshots" in payload["database_counts"]
    assert "alerts" in payload["database_counts"]
    assert "notification_logs" in payload["database_counts"]


def test_system_readiness_returns_operational_checks():
    with TestClient(app) as client:
        response = client.get("/system/readiness")

    assert response.status_code == 200
    payload = response.json()

    assert "ready" in payload
    assert "automatic_monitoring_ready" in payload
    assert "scheduler_enabled" in payload
    assert "checks" in payload
    assert "issues" in payload
    assert "warnings" in payload

    checks = payload["checks"]

    assert "provider_usage" in checks
    assert "provider_plan" in checks
    assert "bookmakers" in checks
    assert "competitions" in checks
    assert "markets" in checks
    assert "telegram" in checks
    assert "scheduler" in checks

    assert "ok" in checks["provider_usage"]
    assert "cooldown_active" in checks["provider_usage"]
    assert "limit_reached" in checks["provider_usage"]
    assert "ok" in checks["provider_plan"]
    assert "ok" in checks["bookmakers"]
    assert "ok" in checks["competitions"]
    assert "ok" in checks["markets"]
    assert "ok" in checks["telegram"]
    assert "enabled" in checks["scheduler"]
    assert "loop_running" in checks["scheduler"]
    assert "active_mapped_football_count" in checks["competitions"]
    assert "active_mapped_tennis_count" in checks["competitions"]


def test_provider_usage_returns_usage_status():
    with TestClient(app) as client:
        response = client.get("/system/provider-usage")

    assert response.status_code == 200
    payload = response.json()

    assert payload["provider"] == "odds_api_io"
    assert "hourly_request_limit" in payload
    assert "requests_used_last_hour" in payload
    assert "requests_remaining" in payload
    assert "limit_reached" in payload
    assert "cooldown_active" in payload
    assert "cooldown_until" in payload
    assert "cooldown_reason" in payload
    assert "requests_used_current_hour" in payload
    assert "current_window_start" in payload
    assert "current_window_reset_at" in payload
    assert (
        payload["current_window_reset_at"].endswith("+01:00")
        or payload["current_window_reset_at"].endswith("+02:00")
    )
    assert "message" in payload


def test_provider_usage_counts_requests_in_current_hour_window(tmp_path):
    db = make_usage_test_db(tmp_path)
    now = datetime(2026, 5, 23, 10, 30)

    try:
        db.add(
            ProviderPlanSetting(
                plan_name="Starter",
                hourly_request_limit=5000,
                max_bookmakers=2,
                created_at=now,
            )
        )
        for created_at in [
            datetime(2026, 5, 23, 9, 59),
            datetime(2026, 5, 23, 10, 0),
            datetime(2026, 5, 23, 10, 59),
            datetime(2026, 5, 23, 11, 0),
        ]:
            db.add(
                ProviderApiRequestLog(
                    provider="odds_api_io",
                    endpoint="/v1/events",
                    status_code=200,
                    created_at=created_at,
                )
            )
        db.commit()

        status = get_provider_usage_status(db, now=now)

        assert status["hourly_request_limit"] == 5000
        assert status["requests_used_current_hour"] == 2
        assert status["requests_used_last_hour"] == 2
        assert status["requests_remaining"] == 4998
        assert status["current_window_start"] == "2026-05-23T12:00:00+02:00"
        assert status["current_window_reset_at"] == "2026-05-23T13:00:00+02:00"
    finally:
        db.close()


def test_provider_usage_resets_when_hour_window_changes(tmp_path):
    db = make_usage_test_db(tmp_path)

    try:
        plan = get_or_create_provider_plan_settings(db)
        assert plan.hourly_request_limit == 5000

        db.add(
            ProviderApiRequestLog(
                provider="odds_api_io",
                endpoint="/v1/events",
                status_code=200,
                created_at=datetime(2026, 5, 23, 10, 59),
            )
        )
        db.commit()

        before_reset = get_provider_usage_status(
            db,
            now=datetime(2026, 5, 23, 10, 59, 30),
        )
        after_reset = get_provider_usage_status(
            db,
            now=datetime(2026, 5, 23, 11, 0),
        )

        assert before_reset["requests_used_current_hour"] == 1
        assert before_reset["requests_remaining"] == 4999
        assert after_reset["requests_used_current_hour"] == 0
        assert after_reset["requests_remaining"] == 5000
        assert before_reset["current_window_reset_at"] == "2026-05-23T13:00:00+02:00"
        assert after_reset["current_window_start"] == "2026-05-23T13:00:00+02:00"
    finally:
        db.close()


def test_scheduler_validation_uses_default_5000_hourly_limit(tmp_path):
    db = make_usage_test_db(tmp_path)

    try:
        plan = get_or_create_provider_plan_settings(db)
        assert plan.hourly_request_limit == 5000

        assert validate_scheduler_against_provider_plan(
            db=db,
            enabled=True,
            poll_interval_seconds=3600,
            event_limit=5000,
        ) is None

        with pytest.raises(ValueError):
            validate_scheduler_against_provider_plan(
                db=db,
                enabled=True,
                poll_interval_seconds=3600,
                event_limit=5001,
            )
    finally:
        db.close()
