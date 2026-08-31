from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.owner import Owner
from app.models.person import Person
from app.models.connection import Connection
from app.models.activity_event import ActivityEvent
from app.models.insight import Insight
from app.models.technology import Technology, PersonTechnology
from app.narrative.template import activity_digest, template_narrative
from app.serializers import owner_to_dict, insight_to_dict, event_to_dict, connection_to_dict

router = APIRouter(prefix="/api", tags=["dashboard"])

HIGHLIGHT_THRESHOLD = 8
ACTIVITY_LOOKBACK_DAYS = 30


def _insight_is_usable(insight: Insight | None) -> bool:
    if insight is None:
        return False
    model = (insight.model_used or "").lower()
    if model.startswith("fallback"):
        return False
    text = (insight.narrative_text or "").lower()
    if "routine activity" in text and "no major changes" in text:
        return False
    return True


def _person_payload(person: Person, *, is_close: bool, insight: Insight | None, events: list) -> dict:
    event_dicts = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "repo_full_name": e.repo_full_name,
            "significance_score": e.significance_score,
        }
        for e in events
    ]
    stats = activity_digest(event_dicts)
    person_info = {
        "github_username": person.github_username,
        "display_name": person.display_name,
    }
    if _insight_is_usable(insight):
        narrative = insight.narrative_text
        model = insight.model_used
        supporting = insight.supporting_event_ids
        week_start = insight.week_start.isoformat() if insight.week_start else None
        week_end = insight.week_end.isoformat() if insight.week_end else None
        total = insight.significance_total or stats["significance_total"]
    else:
        narrative, supporting, model = template_narrative(person_info, event_dicts, [])
        week_start = week_end = None
        total = stats["significance_total"]

    latest = None
    if stats["event_count"] or _insight_is_usable(insight):
        latest = {
            "narrative_text": narrative,
            "significance_total": total,
            "supporting_event_ids": supporting,
            "model_used": model,
            "week_start": week_start,
            "week_end": week_end,
        }

    return {
        "id": person.id,
        "github_username": person.github_username,
        "display_name": person.display_name,
        "avatar_url": person.avatar_url,
        "is_close": is_close,
        "event_count": stats["event_count"],
        "top_repos": stats["top_repos"],
        "latest_insight": latest,
    }


@router.get("/owners")
async def list_owners(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Owner).order_by(Owner.id))
    owners = res.scalars().all()
    count_res = await db.execute(
        select(Connection.owner_id, func.count(Connection.id)).group_by(Connection.owner_id)
    )
    counts = {row[0]: row[1] for row in count_res.all()}
    payload = []
    for owner in owners:
        item = owner_to_dict(owner)
        item["connection_count"] = counts.get(owner.id, 0)
        payload.append(item)
    return payload


@router.get("/owners/{owner_id}/digest")
async def get_owner_digest(owner_id: int, db: AsyncSession = Depends(get_db)):
    owner = await db.get(Owner, owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    res = await db.execute(
        select(Connection)
        .options(selectinload(Connection.person).selectinload(Person.insights))
        .where(Connection.owner_id == owner_id)
    )
    connections = res.scalars().all()
    person_ids = [c.person_id for c in connections]

    lookback = datetime.now(timezone.utc) - timedelta(days=ACTIVITY_LOOKBACK_DAYS)
    events_by_person: dict[int, list[ActivityEvent]] = {pid: [] for pid in person_ids}
    if person_ids:
        ev_res = await db.execute(
            select(ActivityEvent)
            .where(
                ActivityEvent.person_id.in_(person_ids),
                ActivityEvent.occurred_at >= lookback,
            )
            .order_by(ActivityEvent.occurred_at.desc())
        )
        for event in ev_res.scalars().all():
            events_by_person.setdefault(event.person_id, []).append(event)

    close_circle = []
    network_highlights = []
    rest_of_network = []

    for conn in connections:
        person = conn.person
        latest_insight = None
        if person.insights:
            latest_insight = sorted(person.insights, key=lambda i: i.week_start, reverse=True)[0]

        person_data = _person_payload(
            person,
            is_close=conn.is_close,
            insight=latest_insight,
            events=events_by_person.get(person.id, []),
        )
        score = (person_data["latest_insight"] or {}).get("significance_total") or 0

        if conn.is_close:
            close_circle.append(person_data)
        elif score >= HIGHLIGHT_THRESHOLD:
            network_highlights.append(person_data)
        else:
            rest_of_network.append(person_data)

    def by_score(item):
        return (item["latest_insight"] or {}).get("significance_total") or 0

    network_highlights.sort(key=by_score, reverse=True)
    close_circle.sort(key=by_score, reverse=True)
    rest_of_network.sort(key=by_score, reverse=True)

    return {
        "owner": owner_to_dict(owner),
        "close_circle": close_circle,
        "network_highlights": network_highlights,
        "rest_of_network": rest_of_network,
        "lookback_days": ACTIVITY_LOOKBACK_DAYS,
        "highlight_threshold": HIGHLIGHT_THRESHOLD,
    }


@router.get("/owners/{owner_id}/connections")
async def get_owner_connections(owner_id: int, db: AsyncSession = Depends(get_db)):
    owner = await db.get(Owner, owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    res = await db.execute(
        select(Connection)
        .options(selectinload(Connection.person))
        .where(Connection.owner_id == owner_id)
        .order_by(Connection.is_close.desc(), Connection.id)
    )
    return [connection_to_dict(c) for c in res.scalars().all()]


@router.get("/people/{person_id}")
async def get_person_detail(person_id: int, db: AsyncSession = Depends(get_db)):
    person = await db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    res = await db.execute(
        select(Technology.name, PersonTechnology.confidence)
        .join(PersonTechnology, PersonTechnology.technology_id == Technology.id)
        .where(PersonTechnology.person_id == person_id)
        .order_by(PersonTechnology.confidence.desc())
    )
    techs = [{"name": row.name, "confidence": row.confidence} for row in res.all()]

    lookback = datetime.now(timezone.utc) - timedelta(days=ACTIVITY_LOOKBACK_DAYS)
    ev_res = await db.execute(
        select(ActivityEvent)
        .where(ActivityEvent.person_id == person_id, ActivityEvent.occurred_at >= lookback)
        .order_by(ActivityEvent.occurred_at.desc())
    )
    recent = ev_res.scalars().all()

    res_insight = await db.execute(
        select(Insight)
        .where(Insight.person_id == person_id)
        .order_by(Insight.week_start.desc())
        .limit(1)
    )
    stored = res_insight.scalar_one_or_none()
    payload = _person_payload(person, is_close=False, insight=stored, events=recent)

    return {
        "id": person.id,
        "github_username": person.github_username,
        "display_name": person.display_name,
        "avatar_url": person.avatar_url,
        "technologies": techs,
        "latest_insight": payload["latest_insight"],
        "event_count": payload["event_count"],
        "top_repos": payload["top_repos"],
    }


@router.get("/people/{person_id}/events")
async def get_person_events(person_id: int, db: AsyncSession = Depends(get_db)):
    person = await db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    res = await db.execute(
        select(ActivityEvent)
        .where(ActivityEvent.person_id == person_id)
        .order_by(ActivityEvent.occurred_at.desc())
        .limit(50)
    )
    return [event_to_dict(e) for e in res.scalars().all()]


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    people_count = await db.scalar(select(func.count()).select_from(Person))
    events_count = await db.scalar(select(func.count()).select_from(ActivityEvent))
    owners_count = await db.scalar(select(func.count()).select_from(Owner))
    insights_count = await db.scalar(select(func.count()).select_from(Insight))
    return {
        "total_owners": owners_count or 0,
        "total_people_tracked": people_count or 0,
        "total_events_collected": events_count or 0,
        "total_insights": insights_count or 0,
    }
