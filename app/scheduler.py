import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db import async_session
from app.pipeline import run_global_pipeline

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _run_pipeline_job() -> None:
    logger.info("Scheduled pipeline starting")
    async with async_session() as session:
        try:
            await run_global_pipeline(session)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Scheduled pipeline failed")


def start_scheduler() -> None:
    scheduler.add_job(
        _run_pipeline_job,
        "interval",
        hours=24,
        id="daily-collect",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_pipeline_job,
        "cron",
        day_of_week="mon",
        hour=8,
        id="weekly-narrative",
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started (daily collect + Monday 08:00 narrative)")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
