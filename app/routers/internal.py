import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Header, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import async_session
from app.models.pipeline_run import PipelineRun
from app.pipeline import run_collect, run_narrate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["internal"])

STALE_RUNNING = timedelta(minutes=30)


def verify_cron_secret(
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
):
    expected = (get_settings().cron_secret or "").strip()
    provided = (x_cron_secret or "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="CRON_SECRET not configured on server")
    if not provided:
        raise HTTPException(status_code=401, detail="Missing X-Cron-Secret header")
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    return True


async def find_running_pipeline(session: AsyncSession) -> PipelineRun | None:
    cutoff = datetime.now(timezone.utc) - STALE_RUNNING
    res = await session.execute(
        select(PipelineRun)
        .where(PipelineRun.status == "running", PipelineRun.started_at >= cutoff)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def _run_pipeline_task(run_id: int, phase: str) -> None:
    async with async_session() as session:
        run = await session.get(PipelineRun, run_id)
        if not run:
            return
        try:
            processed = 0
            if phase in ("collect", "all"):
                processed = await run_collect(session)
            if phase in ("narrate", "all"):
                narrated = await run_narrate(session)
                processed = max(processed, narrated)
            run.status = "ok"
            run.people_processed = processed
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info("Pipeline run (phase=%s) finished: %d people", phase, processed)
        except Exception as e:
            logger.exception("Pipeline run (phase=%s) failed", phase)
            run.status = "error"
            run.error = str(e)[:2000]
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()


@router.post("/run-pipeline")
async def trigger_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    phase: str = Query(default="all", pattern="^(collect|narrate|all)$"),
):
    verify_cron_secret(request.headers.get("X-Cron-Secret"))
    async with async_session() as db:
        existing = await find_running_pipeline(db)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Pipeline already running (started {existing.started_at.isoformat()})",
            )

        run = PipelineRun(phase=phase, status="running")
        db.add(run)
        await db.flush()
        run_id = run.id
        await db.commit()

    background_tasks.add_task(_run_pipeline_task, run_id, phase)
    return {"status": "accepted", "phase": phase, "run_id": run_id}
