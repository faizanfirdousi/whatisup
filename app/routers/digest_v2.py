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
from app.network.intelligence import (
    build_network_intelligence,
    direction_area_for_techs,
    owner_network_alignment,
)
from app.network.feed_selection import primary_tech, repo_ecosystem, select_diverse_stories
from app.network.interestingness import compute_interestingness, personal_note
from app.scoring.canonical import canonical_key, display_name
from app.scoring.technology import extract_technologies
from app.serializers import insight_to_dict

router = APIRouter(prefix="/api", tags=["digest_v2"])

MEANINGFUL_MIN = 5
STORY_LIMIT = 5
FEED_STORY_LIMIT = 6
FEED_DISPLAY_LIMIT = 6
ATTENTION_TYPES = frozenset({"release", "new_project", "external_contribution", "deep_work"})
MIN_ATTENTION_RANK = 38


def _present_story_copy(
    summary: str,
    why: str | None,
    *,
    activity_type: str,
    highlight_why: bool = False,
) -> tuple[str, str | None]:
    """Fold contextual why into the summary unless the insight is unusually complex."""
    if not why:
        return summary, None
    if highlight_why or activity_type in ("exploration",):
        return summary, why
    body = summary.rstrip()
    if body and not body.endswith("."):
        body += "."
    return f"{body} {why}", None


def _eligible_for_attention(story: dict) -> bool:
    activity = story.get("activity_type")
    if activity not in ATTENTION_TYPES:
        return False
    rank = story.get("rank") or 0
    meaningful = story.get("meaningful_changes") or 0
    if activity == "deep_work":
        return meaningful >= 2 or rank >= MIN_ATTENTION_RANK + 10
    return rank >= MIN_ATTENTION_RANK or meaningful >= 2


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
    """Kept for the Network explore page — not shown on the homepage."""
    pulse = facts.get("people_by_activity_level") or {}
    return {
        "more_active": len(pulse.get("more_active") or []),
        "steady": len(pulse.get("steady") or []),
        "quiet": len(pulse.get("quiet") or []),
        "network_size": facts.get("network_size") or 0,
    }


def _story_rank(activity_type: str, meaningful: int, event_count: int) -> int:
    """Legacy significance-only rank — kept for tests; prefer interestingness.total."""
    type_bonus = {
        "release": 40,
        "new_project": 35,
        "external_contribution": 30,
        "deep_work": 15,
        "exploration": 10,
        "routine": 5,
    }.get(activity_type or "routine", 5)
    return meaningful * 12 + type_bonus + min(event_count, 8)


def _owner_context(rows: list[dict], facts: dict) -> tuple[set[str], str | None, dict | None]:
    owner_id = facts.get("owner_person_id")
    if not owner_id:
        return set(), None, None
    for row in rows:
        if row["person"]["id"] != owner_id:
            continue
        events = row.get("events") or []
        techs = {t["name"] for t in _techs_from_events(events)}
        stored = row.get("insight") or {}
        focus = stored.get("focus_area")
        if not focus and events:
            enriched = template_narrative_enriched(
                row["person"], _event_dicts(events), _techs_from_events(events)
            )
            focus = enriched.get("focus_area")
        repos = sorted({e.repo_full_name for e in events if e.repo_full_name})[:4]
        snapshot = {
            "person": row["person"],
            "technologies": list(techs),
            "recent_repos": repos,
            "focus": focus,
        }
        return techs, focus, snapshot
    return set(), None, None


def _build_your_direction(
    snapshot: dict | None,
    *,
    owner_techs: set[str],
    owner_focus: str | None,
    intelligence: dict,
    facts: dict,
) -> dict | None:
    if not snapshot and not owner_techs and not owner_focus:
        return None

    for_you = intelligence.get("for_you") or {}
    similar = for_you.get("similar_people") or []
    overlap = None
    if len(similar) >= 2:
        overlap = f"{len(similar)} people you follow are moving in related areas"
    elif cluster := for_you.get("relevant_cluster"):
        overlap = cluster.get("summary")
    elif alignment := owner_network_alignment(facts, owner_techs):
        overlap = alignment

    tech_keys = owner_techs or set(snapshot.get("technologies") or []) if snapshot else owner_techs
    tech_labels = [display_name(t) for t in sorted(tech_keys)[:6]]
    repos = (snapshot or {}).get("recent_repos") or []
    person = (snapshot or {}).get("person") or {}

    if not tech_labels and not repos and not overlap and not owner_focus:
        return None

    return {
        "person_id": person.get("id"),
        "technologies": tech_labels,
        "recent_repos": repos,
        "focus": owner_focus or (snapshot or {}).get("focus"),
        "network_overlap": overlap,
    }


def build_digest_payload(
    *,
    owner_name: str,
    period: str,
    rows: list[dict],
    facts: dict,
    usernames: dict[int, str] | None = None,
) -> dict:
    """Assemble digest v2 from already-loaded person rows. Used by the route and tests."""
    stories = []
    close_circle = []
    people = []
    usernames = usernames or {row["person"]["id"]: row["person"]["github_username"] for row in rows}
    owner_id = facts.get("owner_person_id")
    owner_techs, owner_focus, owner_snapshot = _owner_context(rows, facts)
    network_rising = {canonical_key(row["name"]) for row in facts.get("rising") or []}

    for row in rows:
        person = row["person"]
        events: list[ActivityEvent] = row["events"]
        person_id = person["id"]
        person_meaningful = sum(1 for event in events if (event.significance_score or 0) >= MEANINGFUL_MIN)
        person_repos = {event.repo_full_name for event in events if event.repo_full_name}

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
        if row["is_close"] and person_id != owner_id:
            tech_display = [display_name(t) for t in technologies[:4]]
            repo_list = list(person_repos)[:3]
            repo_count = len(person_repos)
            activity_summary = None
            if person_meaningful > 0 and repo_count:
                activity_summary = (
                    f"Recent activity across {repo_count} "
                    f"{'repository' if repo_count == 1 else 'repositories'}."
                )
            close_circle.append(
                {
                    "person": person_payload,
                    "direction_area": direction_area_for_techs(technologies),
                    "technologies": tech_display,
                    "meaningful_changes": person_meaningful,
                    "active_repos": repo_list,
                    "activity_summary": activity_summary,
                }
            )
        if events and person_id != owner_id:
            trend = (facts.get("activity_direction") or {}).get(person_id, {})
            interest = compute_interestingness(
                activity_type=activity_type,
                meaningful_changes=person_meaningful,
                technologies=technologies,
                is_close=row["is_close"],
                owner_techs=owner_techs,
                network_rising=network_rising,
                trend_direction=trend.get("direction"),
                has_why=bool(why),
            )
            tech_display = [display_name(t) for t in technologies[:4]]
            tech_keys = [canonical_key(t) for t in technologies]
            repos = list(person_repos)
            note = personal_note(technologies=technologies, owner_techs=owner_techs)
            is_tech_shift = trend.get("direction") == "up" and bool(
                set(tech_keys) & network_rising
            )
            card_summary, card_why = _present_story_copy(
                summary,
                why,
                activity_type=activity_type,
                highlight_why=is_tech_shift,
            )
            stories.append(
                {
                    "id": f"story:person:{person_id}",
                    "type": "person_story",
                    "headline": headline,
                    "summary": card_summary,
                    "why_it_matters": card_why,
                    "personal_note": note,
                    "person": person_payload,
                    "technologies": tech_display,
                    "activity_type": activity_type,
                    "rank": interest["total"],
                    "relevance": interest["relevance"],
                    "primary_tech": primary_tech(technologies),
                    "repo_ecosystem": repo_ecosystem(repos),
                    "is_tech_shift": is_tech_shift,
                    "meaningful_changes": person_meaningful,
                }
            )

    editorial = [story for story in stories if _eligible_for_attention(story)]
    ranked = select_diverse_stories(editorial, limit=FEED_STORY_LIMIT)
    selected = ranked[:FEED_DISPLAY_LIMIT]
    more_stories_count = max(0, len(ranked) - len(selected))
    close_circle = [item for item in close_circle if item.get("meaningful_changes", 0) > 0]
    close_circle.sort(key=lambda item: item["meaningful_changes"], reverse=True)
    pulse = _network_pulse(facts)
    intelligence = build_network_intelligence(
        facts,
        usernames=usernames,
        owner_techs=owner_techs,
        owner_focus=owner_focus,
        close_people=close_circle,
    )
    your_direction = _build_your_direction(
        owner_snapshot,
        owner_techs=owner_techs,
        owner_focus=owner_focus,
        intelligence=intelligence,
        facts=facts,
    )
    return {
        "owner_name": owner_name,
        "greeting": f"Hello, {owner_name}" if owner_name else "Hello",
        "period": period,
        "network_intelligence": intelligence,
        "stories": selected,
        "more_stories_count": more_stories_count,
        "your_direction": your_direction,
        "close_circle": close_circle[:6],
        "network_pulse": pulse,
        "people": people,
    }


@router.get("/me/digest/v2")
async def get_my_digest_v2(
    period: str = "2d",
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
    facts["owner_person_id"] = owner.person_id
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

    usernames = {
        conn.person.id: conn.person.github_username for conn in connections
    }

    name = owner.label or owner.github_username or "there"
    return build_digest_payload(
        owner_name=name,
        period=period,
        rows=rows,
        facts=facts,
        usernames=usernames,
    )
