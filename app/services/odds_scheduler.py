import asyncio
import os
from typing import Optional

from app.database import SessionLocal
from app.services.odds_ingestion_service import ingest_odds_sample


class OddsScheduler:
    def __init__(self):
        self.enabled = os.getenv("ODDS_SCHEDULER_ENABLED", "0") == "1"
        self.interval_seconds = self._get_interval_seconds()
        self.limit = self._get_limit()
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    def _get_interval_seconds(self) -> int:
        raw_value = os.getenv("ODDS_POLL_INTERVAL_SECONDS", "300")

        try:
            value = int(raw_value)
        except ValueError:
            return 300

        if value < 60:
            return 60

        return value

    def _get_limit(self) -> int:
        raw_value = os.getenv("ODDS_SCHEDULER_EVENT_LIMIT", "1")

        try:
            value = int(raw_value)
        except ValueError:
            return 1

        if value < 1:
            return 1

        if value > 10:
            return 10

        return value

    async def start(self):
        if not self.enabled:
            return

        if self._task and not self._task.done():
            return

        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self._stop_event.set()

        if self._task:
            await self._task

    async def _run_loop(self):
        while not self._stop_event.is_set():
            await asyncio.to_thread(self._run_once)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval_seconds,
                )
            except asyncio.TimeoutError:
                continue

    def _run_once(self):
        db = SessionLocal()
        try:
            result = ingest_odds_sample(db=db, limit=self.limit)
            print("[odds-scheduler]", result)
        except Exception as exc:
            print("[odds-scheduler] error:", exc)
        finally:
            db.close()


odds_scheduler = OddsScheduler()
