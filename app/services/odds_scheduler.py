import asyncio
from typing import Optional

from app.database import SessionLocal
from app.services.odds_ingestion_service import ingest_odds_sample
from app.services.scheduler_settings_service import get_or_create_scheduler_settings


class OddsScheduler:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None

    async def start(self):
        if self._task and not self._task.done():
            return

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(self._stop_event))

    async def stop(self):
        if not self._stop_event:
            return

        self._stop_event.set()

        if self._task:
            await self._task

        self._task = None
        self._stop_event = None

    async def _run_loop(self, stop_event: asyncio.Event):
        while not stop_event.is_set():
            interval_seconds = await asyncio.to_thread(self._run_configured_cycle)

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=interval_seconds,
                )
            except asyncio.TimeoutError:
                continue

    def _run_configured_cycle(self) -> int:
        db = SessionLocal()

        try:
            settings = get_or_create_scheduler_settings(db)
            interval_seconds = settings.poll_interval_seconds

            if not settings.enabled:
                return interval_seconds

            result = ingest_odds_sample(db=db, limit=settings.event_limit)
            print("[odds-scheduler]", result)

            return interval_seconds
        except Exception as exc:
            print("[odds-scheduler] error:", exc)
            return 300
        finally:
            db.close()


odds_scheduler = OddsScheduler()
