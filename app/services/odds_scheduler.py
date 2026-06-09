import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from app.database import Base, SessionLocal, engine
from app.runtime import load_environment, run_runtime_migrations
from app.services.odds_ingestion_service import ingest_odds_sample
from app.services.scheduler_settings_service import get_or_create_scheduler_settings


logger = logging.getLogger(__name__)


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OddsScheduler:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._wake_event: Optional[asyncio.Event] = None
        self.last_started_at = None
        self.last_tick_at = None
        self.last_success_at = None
        self.last_error = None

    async def start(self, configured_enabled: Optional[bool] = None):
        if self._task and not self._task.done():
            return

        if configured_enabled is None:
            configured_enabled = await asyncio.to_thread(self._load_configured_enabled)

        if not configured_enabled:
            logger.info("Odds scheduler non avviato: configurazione disabled.")
            return

        self._stop_event = asyncio.Event()
        self._wake_event = asyncio.Event()
        self.last_started_at = _utc_now_naive()
        self._task = asyncio.create_task(
            self._run_loop(self._stop_event, self._wake_event)
        )
        logger.info("Odds scheduler avviato.")

    async def stop(self):
        if not self._stop_event:
            return

        self._stop_event.set()
        if self._wake_event:
            self._wake_event.set()

        if self._task:
            await self._task

        self._task = None
        self._stop_event = None
        self._wake_event = None
        logger.info("Odds scheduler fermato.")

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def runtime_status(self, configured_enabled: bool):
        return {
            "configured_enabled": configured_enabled,
            "runtime_running": self.is_running(),
            "last_started_at": self.last_started_at,
            "last_tick_at": self.last_tick_at,
            "last_success_at": self.last_success_at,
            "last_error": self.last_error,
        }

    def notify_settings_changed(self):
        if self._wake_event:
            self._wake_event.set()

    def _load_configured_enabled(self) -> bool:
        db = SessionLocal()
        try:
            settings = get_or_create_scheduler_settings(db)
            return settings.enabled
        finally:
            db.close()

    async def _run_loop(self, stop_event: asyncio.Event, wake_event: asyncio.Event):
        while not stop_event.is_set():
            interval_seconds = await asyncio.to_thread(self._run_configured_cycle)

            try:
                await asyncio.wait_for(
                    wake_event.wait(),
                    timeout=interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

            wake_event.clear()

    def _run_configured_cycle(self) -> int:
        db = SessionLocal()

        try:
            settings = get_or_create_scheduler_settings(db)
            interval_seconds = settings.poll_interval_seconds

            if not settings.enabled:
                logger.info("Odds scheduler tick saltato: configurazione disabled.")
                return interval_seconds

            self.last_tick_at = _utc_now_naive()
            logger.info(
                "Odds scheduler tick avviato: interval_seconds=%s event_limit=%s",
                interval_seconds,
                settings.event_limit,
            )
            result = ingest_odds_sample(db=db, limit=settings.event_limit)
            self.last_success_at = _utc_now_naive()
            self.last_error = None
            logger.info(
                "Odds scheduler tick completato: sport=%s sports_processed=%s "
                "events_received=%s odds_processed=%s snapshots_inserted=%s "
                "alerts_created=%s notification_logs_created=%s",
                result.get("sport"),
                result.get("sports_processed"),
                result.get("events_received"),
                result.get("odds_processed"),
                result.get("snapshots_inserted"),
                result.get("alerts_created"),
                result.get("notification_logs_created"),
            )

            return interval_seconds
        except Exception as exc:
            self.last_error = str(exc)
            logger.exception("Odds scheduler errore durante il tick.")
            return 300
        finally:
            db.close()


odds_scheduler = OddsScheduler()


def run_once():
    load_environment()
    Base.metadata.create_all(bind=engine)
    run_runtime_migrations()

    db = SessionLocal()
    try:
        settings = get_or_create_scheduler_settings(db)

        if not settings.enabled:
            logger.info("Odds ingestion run-once saltata: scheduler disabled.")
            print({"skipped": True, "reason": "scheduler_disabled"})
            return 0

        result = ingest_odds_sample(db=db, limit=settings.event_limit)
        logger.info(
            "Odds ingestion run-once completata: sport=%s sports_processed=%s "
            "events_received=%s odds_processed=%s snapshots_inserted=%s "
            "alerts_created=%s notification_logs_created=%s",
            result.get("sport"),
            result.get("sports_processed"),
            result.get("events_received"),
            result.get("odds_processed"),
            result.get("snapshots_inserted"),
            result.get("alerts_created"),
            result.get("notification_logs_created"),
        )
        print(result)
        return 0
    except Exception:
        logger.exception("Odds ingestion run-once non completata.")
        return 1
    finally:
        db.close()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "run-once":
        return run_once()

    print("Uso: python -m app.services.odds_scheduler run-once")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
