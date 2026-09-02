from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import date
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
from app.narrative.template import activity_digest
from app.network.facts import get_period_bounds
from app.network.journeys import build_monthly_phases, detect_milestones
from app.serializers import owner_to_dict, insight_to_dict, event_to_dict, connection_to_dict

router = APIRouter(prefix="/api", tags=["dashboard"])

HIGHLIGHT_THRESHOLD = 8


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
            "metadata_": e.metadata_,
        }
        for e in events
    ]
    stats = activity_digest(event_dicts)
    person_info = {
        "github_username": person.github_username,
        "display_name": person.display_name,
    }
    if _insight_is_usable(insight):
        parsed = insight_to_dict(insight) or {}
        narrative = parsed.get("narrative_text") or insight.narrative_text
        model = insight.model_used
        supporting = insight.supporting_event_ids
        week_start = insight.week_start.isoformat() if insight.week_start else None
        week_end = insight.week_end.isoformat() if insight.week_end else None
        total = insight.significance_total or stats["significance_total"]
        headline = parsed.get("headline")
        why_it_matters = parsed.get("why_it_matters")
        focus_area = parsed.get("focus_area")
        activity_type = parsed.get("activity_type")
        technologies = parsed.get("technologies_mentioned") or []
    else:
        from app.narrative.template import template_narrative_enriched

        enriched = template_narrative_enriched(person_info, event_dicts, [])
        narrative = enriched["narrative"]
        supporting = enriched["supporting_event_ids"]
        model = enriched["model_used"]
        week_start = week_end = None
        total = stats["significance_total"]
        headline = enriched["headline"]
        why_it_matters = enriched["why_it_matters"]
        focus_area = enriched["focus_area"]
        activity_type = enriched["activity_type"]
        technologies = enriched["technologies_mentioned"]

    latest = None
    if stats["event_count"] or _insight_is_usable(insight):
        latest = {
            "narrative_text": narrative,
            "significance_total": total,
            "supporting_event_ids": supporting,
            "model_used": model,
            "week_start": week_start,
            "week_end": week_end,
            "headline": headline,
            "why_it_matters": why_it_matters,
            "focus_area": focus_area,
            "activity_type": activity_type,
            "technologies_mentioned": technologies,
        }

    return {
        "id": person.id,
        "github_username": person.github_username,
        "display_name": person.display_name,
        "avatar_url": person.avatar_url,
        "is_close": is_close,
        "event_count": stats["event_count"],
        "top_repos": stats["top_repos"],
        "meaningful_changes": sum(1 for e in events if (e.significance_score or 0) >= 5),
        "latest_insight": latest,
    }


from app.auth.session import get_current_owner
from app.rate_limit import limiter

@router.get("/me/digest")
@limiter.limit("20/minute")
async def get_my_digest(
    request: Request,
    period: str = "2d",
    db: AsyncSession = Depends(get_db),
    owner: Owner = Depends(get_current_owner),
):
    res = await db.execute(
        select(Connection)
        .options(selectinload(Connection.person).selectinload(Person.insights))
        .where(Connection.owner_id == owner.id)
    )
    connections = res.scalars().all()
    person_ids = [c.person_id for c in connections]

    _, _, start_dt, end_dt = get_period_bounds(period)
    events_by_person: dict[int, list[ActivityEvent]] = {pid: [] for pid in person_ids}
    if person_ids:
        ev_res = await db.execute(
            select(ActivityEvent)
            .where(
                ActivityEvent.person_id.in_(person_ids),
                ActivityEvent.occurred_at >= start_dt,
                ActivityEvent.occurred_at <= end_dt,
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
        "period": period,
        "highlight_threshold": HIGHLIGHT_THRESHOLD,
    }


@router.get("/me/connections")
async def get_my_connections(
    tech: str | None = None,
    db: AsyncSession = Depends(get_db),
    owner: Owner = Depends(get_current_owner),
):
    res = await db.execute(
        select(Connection)
        .options(selectinload(Connection.person))
        .where(Connection.owner_id == owner.id)
        .order_by(Connection.is_close.desc(), Connection.id)
    )
    connections = list(res.scalars().all())
    if tech:
        needle = tech.strip().lower()
        person_ids = [c.person_id for c in connections]
        if person_ids:
            tech_res = await db.execute(
                select(PersonTechnology.person_id)
                .join(Technology, Technology.id == PersonTechnology.technology_id)
                .where(
                    PersonTechnology.person_id.in_(person_ids),
                    Technology.name == needle,
                )
            )
            matching = {pid for pid, in tech_res.all()}
            connections = [c for c in connections if c.person_id in matching]
    return [connection_to_dict(c) for c in connections]


async def _verify_person_access(db: AsyncSession, owner_id: int, person_id: int) -> Person:
    res = await db.execute(
        select(Connection).options(selectinload(Connection.person))
        .where(Connection.owner_id == owner_id, Connection.person_id == person_id)
    )
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=403, detail="You are not tracking this person")
    return conn.person


@router.get("/people/{person_id}")
async def get_person_detail(person_id: int, db: AsyncSession = Depends(get_db), owner: Owner = Depends(get_current_owner)):
    person = await _verify_person_access(db, owner.id, person_id)

    res = await db.execute(
        select(Technology.name, PersonTechnology.confidence, PersonTechnology.first_seen_at)
        .join(PersonTechnology, PersonTechnology.technology_id == Technology.id)
        .where(PersonTechnology.person_id == person_id)
        .order_by(PersonTechnology.confidence.desc())
    )
    techs = []
    tech_first_seen: dict[str, date] = {}
    for row in res.all():
        techs.append({"name": row.name, "confidence": row.confidence})
        if row.first_seen_at:
            first = row.first_seen_at.date() if hasattr(row.first_seen_at, "date") else row.first_seen_at
            tech_first_seen[row.name] = first

    _, _, start_dt, end_dt = get_period_bounds("30d")
    ev_res = await db.execute(
        select(ActivityEvent)
        .where(
            ActivityEvent.person_id == person_id,
            ActivityEvent.occurred_at >= start_dt,
            ActivityEvent.occurred_at <= end_dt,
        )
        .order_by(ActivityEvent.occurred_at.desc())
    )
    recent = ev_res.scalars().all()

    journey_res = await db.execute(
        select(ActivityEvent)
        .where(ActivityEvent.person_id == person_id)
        .order_by(ActivityEvent.occurred_at.asc())
        .limit(500)
    )
    journey_events = list(journey_res.scalars().all())
    journey = {
        "phases": build_monthly_phases(journey_events, github_username=person.github_username),
        "milestones": detect_milestones(
            journey_events,
            github_username=person.github_username,
            tech_first_seen=tech_first_seen,
        ),
    }

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
        "journey": journey,
    }


@router.get("/people/{person_id}/events")
async def get_person_events(person_id: int, db: AsyncSession = Depends(get_db), owner: Owner = Depends(get_current_owner)):
    await _verify_person_access(db, owner.id, person_id)

    res = await db.execute(
        select(ActivityEvent)
        .where(ActivityEvent.person_id == person_id)
        .order_by(ActivityEvent.occurred_at.desc())
        .limit(50)
    )
    return [event_to_dict(e) for e in res.scalars().all()]


@router.get("/me/stats")
async def get_my_stats(
    period: str = "2d",
    db: AsyncSession = Depends(get_db),
    owner: Owner = Depends(get_current_owner),
):
    res = await db.execute(select(Connection.person_id).where(Connection.owner_id == owner.id))
    person_ids = [pid for pid, in res.all()]
    
    if not person_ids:
        return {
            "total_people_tracked": 0,
            "total_events_collected": 0,
            "total_insights": 0,
            "events_this_period": 0,
            "events_this_week": 0,
        }

    people_count = len(person_ids)

    _, _, start_dt, end_dt = get_period_bounds(period)
    period_count = 0
    if person_ids:
        week_res = await db.execute(
            select(func.count())
            .select_from(ActivityEvent)
            .where(
                ActivityEvent.person_id.in_(person_ids),
                ActivityEvent.occurred_at >= start_dt,
                ActivityEvent.occurred_at <= end_dt,
            )
        )
        period_count = week_res.scalar() or 0

    ev_count_res = await db.execute(
        select(func.count()).select_from(ActivityEvent).where(ActivityEvent.person_id.in_(person_ids))
    )
    events_count = ev_count_res.scalar() or 0
    
    in_count_res = await db.execute(
        select(func.count()).select_from(Insight).where(Insight.person_id.in_(person_ids))
    )
    insights_count = in_count_res.scalar() or 0
    
    return {
        "total_people_tracked": people_count,
        "total_events_collected": events_count,
        "total_insights": insights_count,
        "events_this_period": period_count,
        "events_this_week": period_count,
        "period": period,
    }
