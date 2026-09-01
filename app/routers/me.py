import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_owner
from app.db import async_session, get_db
from app.models.connection import Connection
from app.models.network_story import NetworkStory
from app.models.owner import Owner
from app.narrative.network_story import template_network_story
from app.network.facts import all_person_ids_from_facts, compute_network_facts, get_period_bounds
from app.pipeline import current_week_bounds, owner_collect_allowed, run_collect_for_owner
from app.scoring.since import compute_since_items, default_since

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["me"])


class AckBody(BaseModel):
    surface: str = "dashboard"
    item_ids: list[str] | None = None


class ConnectionUpdate(BaseModel):
    is_close: bool


def _owner_public(owner: Owner) -> dict:
    collecting = owner.collect_in_progress_at is not None
    return {
        "id": owner.id,
        "github_username": owner.github_username,
        "label": owner.label,
        "is_builder": owner.is_builder,
        "person_id": owner.person_id,
        "last_collected_at": owner.last_collected_at.isoformat() if owner.last_collected_at else None,
        "highlights_acked_at": owner.highlights_acked_at.isoformat() if owner.highlights_acked_at else None,
        "collecting": collecting,
    }


@router.get("/me")
async def get_me(owner: Owner = Depends(get_current_owner)):
    return _owner_public(owner)


async def _owner_collect_task(owner_id: int) -> None:
    async with async_session() as session:
        try:
            await run_collect_for_owner(session, owner_id)
        except Exception:
            logger.exception("Owner collect failed for %s", owner_id)
            owner = await session.get(Owner, owner_id)
            if owner:
                owner.collect_in_progress_at = None
                await session.commit()


async def _maybe_start_collect(
    session: AsyncSession, owner: Owner, background_tasks: BackgroundTasks
) -> bool:
    allowed, _reason = owner_collect_allowed(owner)
    if not allowed:
        return owner.collect_in_progress_at is not None
    owner.collect_in_progress_at = datetime.now(timezone.utc)
    await session.commit()
    background_tasks.add_task(_owner_collect_task, owner.id)
    return True


async def _highlights_payload(session: AsyncSession, owner: Owner, period: str = "7d") -> dict:
    _, _, period_start, _ = get_period_bounds(period)
    since = max(default_since(owner.highlights_acked_at), period_start)
    items = await compute_since_items(session, owner, since=since)
    collecting = owner.collect_in_progress_at is not None
    return {
        "since": since.isoformat(),
        "collected_at": owner.last_collected_at.isoformat() if owner.last_collected_at else None,
        "collecting": collecting,
        "title": "Worth your attention",
        "period": period,
        "unread_count": len(items),
        "items": items,
    }


@router.get("/me/since")
async def get_since(
    period: str = "7d",
    db: AsyncSession = Depends(get_db),
    owner: Owner = Depends(get_current_owner),
):
    payload = await _highlights_payload(db, owner, period)
    payload["empty_copy"] = "No meaningful changes yet. We'll highlight changes here as your network becomes active."
    return payload


@router.get("/me/highlights")
async def get_highlights(
    background_tasks: BackgroundTasks,
    refresh: int = Query(default=0),
    period: str = "7d",
    db: AsyncSession = Depends(get_db),
    owner: Owner = Depends(get_current_owner),
):
    started = False
    if refresh:
        started = await _maybe_start_collect(db, owner, background_tasks)
    payload = await _highlights_payload(db, owner, period)
    if started:
        payload["collecting"] = True
    return payload


@router.post("/me/collect")
async def post_collect(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    owner: Owner = Depends(get_current_owner),
):
    allowed, reason = owner_collect_allowed(owner)
    started = False
    if allowed:
        started = await _maybe_start_collect(db, owner, background_tasks)
        reason = "started"
    return {
        "accepted": started,
        "reason": reason,
        "collecting": owner.collect_in_progress_at is not None,
        "collected_at": owner.last_collected_at.isoformat() if owner.last_collected_at else None,
    }


@router.post("/me/ack")
async def post_ack(
    body: AckBody,
    db: AsyncSession = Depends(get_db),
    owner: Owner = Depends(get_current_owner),
):
    owner.highlights_acked_at = datetime.now(timezone.utc)
    return {
        "acked_at": owner.highlights_acked_at.isoformat(),
        "surface": body.surface,
        "item_ids": body.item_ids,
    }


@router.patch("/me/connections/{connection_id}")
async def patch_connection(
    connection_id: int,
    update: ConnectionUpdate,
    db: AsyncSession = Depends(get_db),
    owner: Owner = Depends(get_current_owner),
):
    conn = await db.get(Connection, connection_id)
    if not conn or conn.owner_id != owner.id:
        raise HTTPException(status_code=404, detail="Connection not found")
    conn.is_close = update.is_close
    return {"status": "success", "connection_id": conn.id, "is_close": conn.is_close}


@router.get("/me/network-story")
async def get_network_story(
    db: AsyncSession = Depends(get_db), owner: Owner = Depends(get_current_owner)
):
    week_start, week_end, _, _ = current_week_bounds()
    res = await db.execute(
        select(NetworkStory)
        .where(NetworkStory.owner_id == owner.id)
        .order_by(NetworkStory.week_start.desc())
        .limit(1)
    )
    row = res.scalar_one_or_none()
    if row:
        try:
            parsed = json.loads(row.narrative_text)
        except json.JSONDecodeError:
            parsed = {"headline": "Your network this week", "bullets": [row.narrative_text], "interesting": None}
        return {
            "week_start": row.week_start.isoformat(),
            "week_end": row.week_end.isoformat(),
            "facts": row.facts,
            "model_used": row.model_used,
            "source": "stored",
            **parsed,
        }

    facts = await compute_network_facts(db, owner.id)
    ids = list(all_person_ids_from_facts(facts))
    usernames: dict[int, str] = {}
    if ids:
        from app.models.person import Person

        pres = await db.execute(select(Person.id, Person.github_username).where(Person.id.in_(ids)))
        usernames = {r.id: r.github_username for r in pres.all()}
    templated = template_network_story(facts, usernames)
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "facts": facts,
        "model_used": "template",
        "source": "on_read",
        **templated.model_dump(),
    }
