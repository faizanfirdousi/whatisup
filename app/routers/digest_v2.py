from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.session import get_current_owner
from app.db import get_db
from app.models.activity_event import ActivityEvent
from app.models.connection import Connection
from app.models.insight import Insight
from app.models.owner import Owner
from app.models.person import Person
from app.narrative.template import template_narrative_enriched
from app.network.facts import compute_network_facts, get_period_bounds
from app.scoring.technology import extract_technologies
from app.serializers import insight_to_dict

router = APIRouter(prefix="/api", tags=["digest_v2"])

MEANINGFUL_MIN = 5
STORY_LIMIT = 8


def _insight_covers_period(insight: Insight | None, start: date, end: date) -> bool:
    if insight is None or insight.week_start is None:
        return False
    week_end = insight.week_end or insight.week_start
    return insight.week_start <= end and week_end >= start


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


def _techs_from_events(events: list[ActivityEvent]) -> list[dict]:
    seen: set[str] = set()
    techs: list[dict] = []
    for event in events:
        for tech in extract_technologies(event.metadata_ or {}):
            name = (tech.get("name") or "").lower()
            if name and name not in seen:
                seen.add(name)
                techs.append(tech)
    return techs


def _event_dicts(events: list[ActivityEvent]) -> list[dict]:
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "repo_full_name": event.repo_full_name,
            "significance_score": event.significance_score,
            "metadata_": event.metadata_,
        }
        for event in events
    ]


def _activity_level(facts: dict, person_id: int) -> str:
    buckets = facts.get("people_by_activity_level") or {}
    for level, ids in buckets.items():
        if person_id in ids:
            return level
    return "quiet"


def _network_pulse(facts: dict) -> dict:
    pulse = facts.get("people_by_activity_level") or {}
    top_techs = []
    for row in facts.get("tech_this_week") or []:
        top_techs.append(
            {
                "name": row["name"],
                "people_count": len(row.get("person_ids") or []),
                "direction": "steady",
            }
        )
    rising = {row["name"] for row in facts.get("rising") or []}
    for tech in top_techs:
        if tech["name"] in rising:
            tech["direction"] = "up"
    for row in facts.get("declining") or []:
        top_techs.append({"name": row["name"], "people_count": 0, "direction": "down"})
    top_techs.sort(key=lambda item: item["people_count"], reverse=True)
    return {
        "more_active": len(pulse.get("more_active") or []),
        "steady": len(pulse.get("steady") or []),
        "quiet": len(pulse.get("quiet") or []),
        "top_technologies": top_techs[:5],
        "network_size": facts.get("network_size") or 0,
    }


def _emerging(facts: dict) -> list[dict]:
    emerging = []
    for row in facts.get("rising") or []:
        emerging.append(
            {
                "type": "tech_cluster",
                "headline": f"{row['name'].capitalize()} is becoming more common across your network",
                "technologies": [row["name"]],
                "people_count": row["this_week_people"],
            }
        )
    for row in facts.get("new_in_network") or []:
        emerging.append(
            {
                "type": "tech_cluster",
                "headline": f"{row['name'].capitalize()} is new in your network",
                "technologies": [row["name"]],
                "people_count": len(row.get("person_ids") or []),
            }
        )
    for row in facts.get("shared_repos") or []:
        emerging.append(
            {
                "type": "shared_repo",
                "headline": f"{row['people_count']} people interacted with {row['repo']}",
                "repo": row["repo"],
                "people_count": row["people_count"],
            }
        )
    return emerging[:5]


def _story_rank(activity_type: str, meaningful: int, event_count: int) -> int:
    type_bonus = {
        "release": 40,
        "new_project": 35,
        "external_contribution": 30,
        "deep_work": 15,
        "exploration": 10,
        "routine": 5,
    }.get(activity_type or "routine", 5)
    return meaningful * 12 + type_bonus + min(event_count, 8)


def build_digest_payload(
    *,
    owner_name: str,
    period: str,
    rows: list[dict],
    facts: dict,
) -> dict:
    """Assemble digest v2 from already-loaded person rows. Used by the route and tests."""
    stories = []
    close_circle = []
    people = []
    people_shipped_ids: set[int] = set()
    new_projects = 0
    interesting_repos: set[str] = set()
    meaningful_changes = 0

    for row in rows:
        person = row["person"]
        events: list[ActivityEvent] = row["events"]
        person_id = person["id"]
        person_meaningful = sum(1 for event in events if (event.significance_score or 0) >= MEANINGFUL_MIN)
        person_repos = {event.repo_full_name for event in events if event.repo_full_name}
        meaningful_changes += person_meaningful
        for event in events:
            if event.event_type == "release_published":
                people_shipped_ids.add(person_id)
            if event.event_type == "repository_created":
                new_projects += 1
            if event.repo_full_name and (event.significance_score or 0) >= MEANINGFUL_MIN:
                interesting_repos.add(event.repo_full_name)

        techs = _techs_from_events(events)
        enriched = template_narrative_enriched(person, _event_dicts(events), techs)
        stored = row.get("insight") or {}
        if stored:
            headline = stored.get("headline") or enriched["headline"]
            summary = stored.get("narrative_text") or enriched["narrative"]
            why = stored.get("why_it_matters") or enriched["why_it_matters"]
            focus = stored.get("focus_area") or enriched["focus_area"]
            activity_type = stored.get("activity_type") or enriched["activity_type"]
            technologies = stored.get("technologies_mentioned") or enriched["technologies_mentioned"]
        else:
            headline = enriched["headline"]
            summary = enriched["narrative"]
            why = enriched["why_it_matters"]
            focus = enriched["focus_area"]
            activity_type = enriched["activity_type"]
            technologies = enriched["technologies_mentioned"]

        person_payload = {
            "id": person_id,
            "github_username": person["github_username"],
            "display_name": person.get("display_name"),
            "avatar_url": person.get("avatar_url"),
        }
        trend = (facts.get("activity_direction") or {}).get(person_id, {})
        activity_level = _activity_level(facts, person_id)
        people.append(
            {
                "connection_id": row["connection_id"],
                "is_close": row["is_close"],
                "person": person_payload,
                "headline": headline if events else None,
                "activity_type": activity_type if events else "quiet",
                "activity_level": activity_level,
                "current_focus": focus,
                "meaningful_changes": person_meaningful,
                "technologies": technologies[:5],
            }
        )
        if row["is_close"]:
            close_circle.append(
                {
                    "person": person_payload,
                    "current_focus": focus,
                    "meaningful_changes": person_meaningful,
                    "active_repos": list(person_repos)[:3],
                }
            )
        if events:
            stories.append(
                {
                    "id": f"story:person:{person_id}",
                    "type": "person_story",
                    "headline": headline,
                    "summary": summary,
                    "why_it_matters": why,
                    "person": person_payload,
                    "technologies": technologies[:5],
                    "activity_type": activity_type,
                    "rank": _story_rank(activity_type, person_meaningful, len(events)),
                    "trend": trend,
                    "meaningful_changes": person_meaningful,
                }
            )

    stories.sort(key=lambda item: item["rank"], reverse=True)
    strong_types = {"release", "new_project", "external_contribution", "deep_work"}
    editorial = [
        story
        for story in stories
        if story["activity_type"] in strong_types
        or story.get("why_it_matters")
        or (story.get("meaningful_changes") or 0) > 0
    ]
    selected = (editorial or stories)[:STORY_LIMIT]
    close_circle.sort(key=lambda item: item["meaningful_changes"], reverse=True)
    pulse = _network_pulse(facts)
    return {
        "owner_name": owner_name,
        "greeting": f"Hello, {owner_name}" if owner_name else "Hello",
        "period": period,
        "summary": {
            "meaningful_changes": meaningful_changes,
            "people_shipped": len(people_shipped_ids),
            "new_projects": new_projects,
            "interesting_repos": len(interesting_repos),
            "people_count": pulse["network_size"],
        },
        "stories": selected,
        "close_circle": close_circle,
        "network_pulse": pulse,
        "emerging": _emerging(facts),
        "people": people,
    }


@router.get("/me/digest/v2")
async def get_my_digest_v2(
    period: str = "7d",
    db: AsyncSession = Depends(get_db),
    owner: Owner = Depends(get_current_owner),
):
    week_start, week_end, start_dt, end_dt = get_period_bounds(period)

    res = await db.execute(
        select(Connection)
        .options(selectinload(Connection.person).selectinload(Person.insights))
        .where(Connection.owner_id == owner.id)
    )
    connections = res.scalars().all()
    person_ids = [conn.person_id for conn in connections]

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

    facts = await compute_network_facts(db, owner.id, period=period)
    rows = []
    for conn in connections:
        person = conn.person
        latest = None
        if person.insights:
            latest = sorted(person.insights, key=lambda insight: insight.week_start, reverse=True)[0]
        stored = None
        if _insight_is_usable(latest) and _insight_covers_period(latest, week_start, week_end):
            stored = insight_to_dict(latest)
        rows.append(
            {
                "connection_id": conn.id,
                "is_close": conn.is_close,
                "person": {
                    "id": person.id,
                    "github_username": person.github_username,
                    "display_name": person.display_name,
                    "avatar_url": person.avatar_url,
                },
                "events": events_by_person.get(person.id, []),
                "insight": stored,
            }
        )

    name = owner.label or owner.github_username or "there"
    return build_digest_payload(owner_name=name, period=period, rows=rows, facts=facts)
