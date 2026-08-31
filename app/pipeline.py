import logging
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.person import Person
from app.models.connection import Connection
from app.models.activity_event import ActivityEvent
from app.models.technology import Technology, PersonTechnology
from app.models.insight import Insight

from app.github.collector import (
    fetch_user,
    fetch_following,
    fetch_public_events,
    fetch_repo_metadata,
)
from app.github.normalize import normalize_event
from app.scoring.significance import score_event
from app.scoring.technology import extract_technologies
from app.narrative.generate import generate_weekly_narrative

logger = logging.getLogger(__name__)


def current_week_bounds(today: date | None = None) -> tuple[date, date, datetime, datetime]:
    today = today or date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(week_end, datetime.max.time(), tzinfo=timezone.utc)
    return week_start, week_end, start_dt, end_dt


def build_score_context(event: dict, person: Person, has_existing_repo: bool) -> dict:
    context: dict = {}
    if event["event_type"] == "repository_created" and not has_existing_repo:
        context["is_first_repo"] = True

    repo_name = event.get("repo_full_name") or ""
    if "/" in repo_name:
        repo_owner = repo_name.split("/", 1)[0]
        if repo_owner.lower() != person.github_username.lower():
            context["is_external"] = True
    return context


async def get_or_create_person(session: AsyncSession, github_user: dict) -> Person:
    result = await session.execute(select(Person).where(Person.github_id == github_user["id"]))
    person = result.scalar_one_or_none()

    if not person:
        person = Person(
            github_id=github_user["id"],
            github_username=github_user["login"],
            display_name=github_user.get("name"),
            avatar_url=github_user.get("avatar_url"),
            profile_last_synced_at=datetime.now(timezone.utc),
        )
        session.add(person)
        await session.flush()
        return person

    person.github_username = github_user["login"]
    if github_user.get("name"):
        person.display_name = github_user.get("name")
    if github_user.get("avatar_url"):
        person.avatar_url = github_user.get("avatar_url")
    person.profile_last_synced_at = datetime.now(timezone.utc)
    return person


async def _ensure_connection(
    session: AsyncSession, owner_id: int, person: Person, is_close: bool
) -> None:
    result = await session.execute(
        select(Connection).where(
            Connection.owner_id == owner_id,
            Connection.person_id == person.id,
        )
    )
    existing = result.scalar_one_or_none()
    if not existing:
        session.add(Connection(owner_id=owner_id, person_id=person.id, is_close=is_close))
    elif is_close and not existing.is_close:
        existing.is_close = True


async def seed_connections_for_owner(
    session: AsyncSession, owner_id: int, github_username: str
) -> dict:
    """Track the owner themselves plus everyone they follow. Does not commit."""
    owner_user = await fetch_user(github_username)
    owner_person = await get_or_create_person(session, owner_user)
    await _ensure_connection(session, owner_id, owner_person, is_close=True)

    following = await fetch_following(github_username)
    for user in following:
        person = await get_or_create_person(session, user)
        await _ensure_connection(session, owner_id, person, is_close=False)

    await session.flush()
    return {
        "owner_person_id": owner_person.id,
        "following_count": len(following),
        "tracked_including_self": len(following) + 1,
    }


def _session_technology(session: AsyncSession, name: str) -> Technology | None:
    for obj in list(session.new) + list(session.identity_map.values()):
        if isinstance(obj, Technology) and obj.name == name:
            return obj
    return None


async def _get_or_create_technology(
    session: AsyncSession, name: str, cache: dict[str, Technology]
) -> Technology:
    name = name.strip().lower()
    if name in cache:
        return cache[name]

    cached = _session_technology(session, name)
    if cached is not None:
        cache[name] = cached
        return cached

    result = await session.execute(select(Technology).where(Technology.name == name))
    tech = result.scalar_one_or_none()
    if tech is None:
        await session.execute(
            pg_insert(Technology).values(name=name).on_conflict_do_nothing(index_elements=["name"])
        )
        await session.flush()
        result = await session.execute(select(Technology).where(Technology.name == name))
        tech = result.scalar_one()

    cache[name] = tech
    return tech


async def _upsert_person_technologies(
    session: AsyncSession,
    person_id: int,
    techs: list[dict],
    cache: dict[str, Technology],
) -> None:
    now = datetime.now(timezone.utc)
    for t in techs:
        name = (t.get("name") or "").strip().lower()
        if not name:
            continue
        tech_obj = await _get_or_create_technology(session, name, cache)
        insert_stmt = pg_insert(PersonTechnology).values(
            person_id=person_id,
            technology_id=tech_obj.id,
            confidence=t["confidence"],
            last_seen_at=now,
        )
        await session.execute(
            insert_stmt.on_conflict_do_update(
                index_elements=["person_id", "technology_id"],
                set_={
                    "last_seen_at": now,
                    "confidence": func.greatest(
                        PersonTechnology.confidence, insert_stmt.excluded.confidence
                    ),
                },
            )
        )


async def run_pipeline_for_person(
    session: AsyncSession,
    person_id: int,
    tech_cache: dict[str, Technology] | None = None,
) -> None:
    person = await session.get(Person, person_id)
    if not person:
        return

    logger.info("Running pipeline for %s", person.github_username)
    tech_cache = tech_cache if tech_cache is not None else {}

    events_data = await fetch_public_events(person.github_username)
    seen_repos: set[str] = set()

    for raw_event in events_data:
        norm = normalize_event(raw_event, person.id)
        if not norm:
            continue

        result = await session.execute(
            select(ActivityEvent).where(
                ActivityEvent.source == norm["source"],
                ActivityEvent.external_event_id == norm["external_event_id"],
            )
        )
        if result.scalar_one_or_none():
            continue

        repo_name = norm["repo_full_name"]
        if repo_name and repo_name not in seen_repos and "/" in repo_name:
            owner_name, repo_only = repo_name.split("/", 1)
            meta = await fetch_repo_metadata(owner_name, repo_only)
            norm["metadata_"] = meta
            seen_repos.add(repo_name)
            await _upsert_person_technologies(
                session, person.id, extract_technologies(meta), tech_cache
            )

        has_existing_repo = False
        if norm["event_type"] == "repository_created":
            res = await session.execute(
                select(ActivityEvent)
                .where(
                    ActivityEvent.person_id == person.id,
                    ActivityEvent.event_type == "repository_created",
                )
                .limit(1)
            )
            has_existing_repo = res.scalar_one_or_none() is not None

        norm["significance_score"] = score_event(
            norm, build_score_context(norm, person, has_existing_repo)
        )
        session.add(ActivityEvent(**norm))

    await session.commit()

    week_start, week_end, start_dt, end_dt = current_week_bounds()
    res = await session.execute(
        select(ActivityEvent).where(
            ActivityEvent.person_id == person.id,
            ActivityEvent.occurred_at >= start_dt,
            ActivityEvent.occurred_at <= end_dt,
        )
    )
    week_events = list(res.scalars().all())

    # Calendar weeks are empty early in the week; fall back to recent stored events.
    if not week_events:
        lookback = datetime.now(timezone.utc) - timedelta(days=14)
        res = await session.execute(
            select(ActivityEvent)
            .where(
                ActivityEvent.person_id == person.id,
                ActivityEvent.occurred_at >= lookback,
            )
            .order_by(ActivityEvent.occurred_at.desc())
        )
        week_events = list(res.scalars().all())

    if not week_events:
        logger.info("No recent events for %s", person.github_username)
        return

    res = await session.execute(
        select(Technology.name, PersonTechnology.confidence)
        .join(PersonTechnology, PersonTechnology.technology_id == Technology.id)
        .where(PersonTechnology.person_id == person.id)
    )
    person_techs = [{"name": row.name, "confidence": row.confidence} for row in res.all()]

    person_dict = {
        "github_username": person.github_username,
        "display_name": person.display_name,
    }
    events_dicts = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "repo_full_name": e.repo_full_name,
            "occurred_at": e.occurred_at,
            "significance_score": e.significance_score,
            "metadata_": e.metadata_,
        }
        for e in week_events
    ]

    narrative, event_ids, model = await generate_weekly_narrative(
        person_dict, events_dicts, person_techs
    )
    total_score = sum(e.significance_score for e in week_events)

    res = await session.execute(
        select(Insight).where(Insight.person_id == person.id, Insight.week_start == week_start)
    )
    insight = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if insight:
        insight.narrative_text = narrative
        insight.supporting_event_ids = event_ids
        insight.significance_total = total_score
        insight.model_used = model
        insight.generated_at = now
    else:
        session.add(
            Insight(
                person_id=person.id,
                week_start=week_start,
                week_end=week_end,
                narrative_text=narrative,
                supporting_event_ids=event_ids,
                significance_total=total_score,
                model_used=model,
            )
        )

    await session.commit()
    logger.info("Finished pipeline for %s", person.github_username)


async def run_global_pipeline(session: AsyncSession) -> int:
    """Run pipeline for all tracked people. Returns how many people were processed."""
    res = await session.execute(select(Person.id, Person.github_username))
    people = list(res.all())
    processed = 0
    tech_cache: dict[str, Technology] = {}
    for person_id, username in people:
        try:
            await run_pipeline_for_person(session, person_id, tech_cache)
            processed += 1
        except Exception:
            logger.exception("Error in pipeline for %s", username)
            await session.rollback()
            tech_cache.clear()
    return processed
