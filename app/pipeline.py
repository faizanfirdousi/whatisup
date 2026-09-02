import asyncio
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
    fetch_authenticated_following,
    fetch_user,
    fetch_following,
    fetch_public_events,
    fetch_repo_metadata,
)
from app.github.client import GitHubClient, GitHubRateLimitError
from app.github.normalize import normalize_event
from app.scoring.significance import score_event
from app.scoring.technology import extract_technologies
from app.scoring.canonical import canonical_key
from app.narrative.generate import generate_weekly_narrative_enriched
from app.config import get_settings
from app.db import async_session
from app.network.thresholds import COLLECT_STALE_SECONDS, NARRATE_LLM_MIN_SCORE

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
    session: AsyncSession,
    owner_id: int,
    github_username: str,
    client: GitHubClient | None = None,
) -> dict:
    """Track the owner themselves plus everyone they follow. Does not commit."""
    own_client = client is None
    client = client or GitHubClient()
    try:
        owner_user = await fetch_user(client, github_username)
        owner_person = await get_or_create_person(session, owner_user)
        await _ensure_connection(session, owner_id, owner_person, is_close=True)

        if client.token:
            try:
                following = await fetch_authenticated_following(client)
            except Exception:
                following = await fetch_following(client, github_username)
        else:
            following = await fetch_following(client, github_username)
        for user in following:
            person = await get_or_create_person(session, user)
            await _ensure_connection(session, owner_id, person, is_close=False)

        from app.models.owner import Owner

        owner = await session.get(Owner, owner_id)
        if owner:
            owner.person_id = owner_person.id

        await session.flush()
        return {
            "owner_person_id": owner_person.id,
            "following_count": len(following),
            "tracked_including_self": len(following) + 1,
        }
    finally:
        if own_client:
            await client.close()


def _session_technology(session: AsyncSession, name: str) -> Technology | None:
    for obj in list(session.new) + list(session.identity_map.values()):
        if isinstance(obj, Technology) and obj.name == name:
            return obj
    return None


async def _get_or_create_technology(
    session: AsyncSession, name: str, cache: dict[str, Technology]
) -> Technology:
    name = canonical_key(name.strip().lower())
    if not name:
        raise ValueError("technology name required")
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
            first_seen_at=now,
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


async def _token_for_person(session: AsyncSession, person_id: int) -> str | None:
    from app.models.owner import Owner
    from app.auth.crypto import decrypt_token

    res = await session.execute(
        select(Owner)
        .join(Connection, Connection.owner_id == Owner.id)
        .where(
            Connection.person_id == person_id,
            Owner.is_active.is_(True),
            Owner.encrypted_access_token.is_not(None),
        )
        .order_by(Owner.last_login_at.desc().nulls_last())
        .limit(1)
    )
    owner = res.scalar_one_or_none()
    if owner and owner.encrypted_access_token:
        try:
            return decrypt_token(owner.encrypted_access_token)
        except Exception:
            logger.warning("Could not decrypt token for owner %s", owner.id)
    fallback = get_settings().github_token
    return fallback or None


async def _collect_for_person(
    session: AsyncSession,
    person_id: int,
    tech_cache: dict[str, Technology] | None = None,
    client: GitHubClient | None = None,
) -> None:
    """Collect events, score, and extract tech for one person. No narrative."""
    person = await session.get(Person, person_id)
    if not person:
        return

    logger.info("Collecting events for %s", person.github_username)
    tech_cache = tech_cache if tech_cache is not None else {}
    own_client = client is None
    if client is None:
        token = await _token_for_person(session, person.id)
        if not token:
            logger.info("Skipping %s — no owner token and no fallback PAT", person.github_username)
            return
        client = GitHubClient(token=token)

    try:
        events_data, new_etag = await fetch_public_events(
            client, person.github_username, etag=person.events_etag
        )
        if new_etag:
            person.events_etag = new_etag

        if not events_data:
            logger.info("No new events for %s to process.", person.github_username)
            await session.commit()
            return

        norms: list[dict] = []
        for raw_event in events_data:
            norm = normalize_event(raw_event, person.id)
            if norm:
                norms.append(norm)

        if not norms:
            await session.commit()
            return

        ext_ids = [n["external_event_id"] for n in norms]
        existing_res = await session.execute(
            select(ActivityEvent.external_event_id).where(
                ActivityEvent.source == "github",
                ActivityEvent.external_event_id.in_(ext_ids),
            )
        )
        existing_ids = set(existing_res.scalars().all())
        new_norms = [n for n in norms if n["external_event_id"] not in existing_ids]
        if not new_norms:
            await session.commit()
            return

        repos_needed: list[str] = []
        seen_repos: set[str] = set()
        for n in new_norms:
            repo_name = n.get("repo_full_name") or ""
            if repo_name and "/" in repo_name and repo_name not in seen_repos:
                seen_repos.add(repo_name)
                repos_needed.append(repo_name)

        repo_meta: dict[str, dict] = {}
        if repos_needed:
            fetched = await asyncio.gather(
                *[
                    fetch_repo_metadata(client, full.split("/", 1)[0], full.split("/", 1)[1])
                    for full in repos_needed
                ]
            )
            repo_meta = dict(zip(repos_needed, fetched))
            for meta in repo_meta.values():
                await _upsert_person_technologies(
                    session, person.id, extract_technologies(meta), tech_cache
                )

        has_existing_repo = False
        if any(n["event_type"] == "repository_created" for n in new_norms):
            res_repo = await session.execute(
                select(ActivityEvent.id)
                .where(
                    ActivityEvent.person_id == person.id,
                    ActivityEvent.event_type == "repository_created",
                )
                .limit(1)
            )
            has_existing_repo = res_repo.scalar_one_or_none() is not None

        for norm in new_norms:
            repo_name = norm.get("repo_full_name") or ""
            meta: dict = dict(repo_meta.get(repo_name) or {})
            work = norm.get("metadata_") or {}
            for key in ("titles", "commit_subjects", "work_kinds"):
                if work.get(key):
                    meta[key] = work[key]
            context = build_score_context(norm, person, has_existing_repo)
            if context.get("is_external"):
                meta["is_external"] = True
            if norm["event_type"] == "repository_created":
                has_existing_repo = True
            norm["metadata_"] = meta
            norm["significance_score"] = score_event(norm, context)
            session.add(ActivityEvent(**norm))

        await session.commit()
    finally:
        if own_client:
            await client.close()

    logger.info("Finished collecting for %s", person.github_username)



async def _narrate_for_person(
    session: AsyncSession,
    person_id: int,
    tech_cache: dict[str, Technology] | None = None,
) -> None:
    """Generate weekly narrative for one person."""
    person = await session.get(Person, person_id)
    if not person:
        return

    logger.info("Generating narrative for %s", person.github_username)
    tech_cache = tech_cache if tech_cache is not None else {}

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
            "raw_payload": e.raw_payload,
        }
        for e in week_events
    ]

    total_score = sum(e.significance_score for e in week_events)
    skip_llm = total_score < NARRATE_LLM_MIN_SCORE
    if skip_llm:
        from app.narrative.template import template_narrative_enriched

        enriched = template_narrative_enriched(person_dict, events_dicts, person_techs)
    else:
        enriched = await generate_weekly_narrative_enriched(
            person_dict, events_dicts, person_techs
        )

    import json
    narrative_json = json.dumps(enriched)
    event_ids = enriched.get("supporting_event_ids", [])
    model = enriched.get("model_used", "unknown")

    res = await session.execute(
        select(Insight).where(Insight.person_id == person.id, Insight.week_start == week_start)
    )
    insight = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if insight:
        insight.narrative_text = narrative_json
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
                narrative_text=narrative_json,
                supporting_event_ids=event_ids,
                significance_total=total_score,
                model_used=model,
            )
        )

    await session.commit()
    logger.info("Finished narrative for %s", person.github_username)


async def run_pipeline_for_person(
    session: AsyncSession,
    person_id: int,
    tech_cache: dict[str, Technology] | None = None,
) -> None:
    """Full pipeline: collect + narrate for one person. Kept for backward compatibility."""
    await _collect_for_person(session, person_id, tech_cache)
    await _narrate_for_person(session, person_id, tech_cache)


async def _owner_token(owner) -> str | None:
    from app.auth.crypto import decrypt_token

    if owner.encrypted_access_token:
        try:
            return decrypt_token(owner.encrypted_access_token)
        except Exception:
            logger.warning("Could not decrypt token for owner %s", owner.id)
    return get_settings().github_token or None


def collect_is_stale(owner, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    started = owner.collect_in_progress_at
    if started is None:
        return False
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return (now - started).total_seconds() > COLLECT_STALE_SECONDS


def owner_collect_allowed(owner, now: datetime | None = None) -> tuple[bool, str]:
    now = now or datetime.now(timezone.utc)
    if owner.collect_in_progress_at and not collect_is_stale(owner, now):
        return False, "in_progress"
    last = owner.last_collected_at
    if last is not None:
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        min_interval = get_settings().collect_min_interval
        if (now - last).total_seconds() < min_interval:
            return False, "debounced"
    return True, "ok"


async def _collect_people_parallel(
    person_ids: list[int], client: GitHubClient | None = None
) -> int:
    """Collect many people with a bounded number of concurrent GitHub sessions."""
    if not person_ids:
        return 0
    concurrency = max(1, get_settings().collect_concurrency)
    sem = asyncio.Semaphore(concurrency)
    processed = 0
    lock = asyncio.Lock()

    async def _one(person_id: int) -> None:
        nonlocal processed
        async with sem:
            async with async_session() as person_session:
                try:
                    await _collect_for_person(
                        person_session, person_id, {}, client=client
                    )
                    async with lock:
                        processed += 1
                except GitHubRateLimitError:
                    logger.warning("GitHub rate limit while collecting person %s", person_id)
                except Exception:
                    logger.exception("Error collecting person %s", person_id)
                    await person_session.rollback()

    await asyncio.gather(*(_one(pid) for pid in person_ids))
    return processed


async def run_collect_for_owner(session: AsyncSession, owner_id: int) -> int:
    """Collect this owner's network only. No narrate."""
    from app.models.owner import Owner

    owner = await session.get(Owner, owner_id)
    if not owner:
        return 0
    token = await _owner_token(owner)
    if not token:
        logger.info("Owner %s has no GitHub token; skip collect", owner_id)
        return 0

    res = await session.execute(select(Connection.person_id).where(Connection.owner_id == owner_id))
    person_ids = [pid for pid, in res.all()]
    if owner.person_id and owner.person_id not in person_ids:
        owner_person = await session.get(Person, owner.person_id)
        if owner_person:
            await _ensure_connection(session, owner_id, owner_person, is_close=True)
            person_ids.append(owner.person_id)
            await session.commit()
    client = GitHubClient(token=token)
    try:
        processed = await _collect_people_parallel(person_ids, client=client)
    finally:
        await client.close()
        owner = await session.get(Owner, owner_id)
        if owner:
            owner.last_collected_at = datetime.now(timezone.utc)
            owner.collect_in_progress_at = None
            await session.commit()
    return processed


async def run_collect(session: AsyncSession) -> int:
    """Collect events for the union of people connected to active owners."""
    from app.models.owner import Owner

    res = await session.execute(select(Owner).where(Owner.is_active.is_(True)))
    owners = list(res.scalars().all())
    person_ids: set[int] = set()
    for owner in owners:
        conn_res = await session.execute(
            select(Connection.person_id).where(Connection.owner_id == owner.id)
        )
        person_ids.update(pid for pid, in conn_res.all())

    if not person_ids and get_settings().github_token:
        res = await session.execute(select(Person.id))
        person_ids = {pid for pid, in res.all()}

    processed = await _collect_people_parallel(list(person_ids))
    return processed


async def run_narrate(session: AsyncSession) -> int:
    """Generate weekly person insights then per-owner network stories."""
    from app.models.owner import Owner
    from app.narrative.network_story import generate_network_story

    res = await session.execute(select(Person.id, Person.github_username))
    people = list(res.all())
    processed = 0
    tech_cache: dict[str, Technology] = {}
    for person_id, username in people:
        try:
            await _narrate_for_person(session, person_id, tech_cache)
            processed += 1
        except Exception:
            logger.exception("Error narrating for %s", username)
            await session.rollback()
            tech_cache.clear()

    owners = await session.execute(select(Owner.id).where(Owner.is_active.is_(True)))
    for owner_id, in owners.all():
        try:
            await generate_network_story(session, owner_id)
            await session.commit()
        except Exception:
            logger.exception("Error generating network story for owner %s", owner_id)
            await session.rollback()
    return processed


async def run_global_pipeline(session: AsyncSession) -> int:
    """Run full pipeline (collect + narrate) for all tracked people. Returns how many people were processed."""
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

