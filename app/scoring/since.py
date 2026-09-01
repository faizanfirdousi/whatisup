"""Since-you-last-looked ranking.

rank = significance_score
     + 20 if is_close
     + 15 if first_external or tech_first_seen
     + 10 if kind == network_cluster
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity_event import ActivityEvent
from app.models.connection import Connection
from app.models.owner import Owner
from app.models.person import Person
from app.models.technology import PersonTechnology, Technology
from app.network.facts import compute_network_facts, event_is_external
from app.network.thresholds import (
    CLOSE_QUIET_MAX_SLOTS,
    HIGH_SIGNIFICANCE_MIN,
    HIGHLIGHTS_LIMIT,
)

EVENT_LABELS = {
    "pull_request_merged": "merged a pull request",
    "pull_request_opened": "opened a pull request",
    "pull_request_reviewed": "reviewed a pull request",
    "repository_created": "created a repository",
    "release_published": "published a release",
    "push": "pushed commits",
    "issue_opened": "opened an issue",
    "fork": "forked a repository",
    "tag_created": "created a tag",
}


def rank_score(
    *,
    significance: int,
    is_close: bool,
    first_external: bool = False,
    tech_first_seen: bool = False,
    kind: str = "",
) -> int:
    score = significance
    if is_close:
        score += 20
    if first_external or tech_first_seen:
        score += 15
    if kind == "network_cluster":
        score += 10
    return score


def display_name(person: Person) -> str:
    return person.display_name or person.github_username


def _item(
    *,
    item_id: str,
    kind: str,
    headline: str,
    reason: str,
    person_id: int | None,
    event_ids: list[int],
    person: Person | None,
    rank: int,
    extra: dict | None = None,
) -> dict:
    payload = {
        "id": item_id,
        "kind": kind,
        "headline": headline,
        "reason": reason,
        "person_id": person_id,
        "event_ids": event_ids,
        "href": f"/person/{person_id}" if person_id else "/network",
        "person_github": person.github_username if person else None,
        "rank": rank,
    }
    if extra:
        payload.update(extra)
    return payload


async def _had_external_pr_before(
    session: AsyncSession, person: Person, before: datetime
) -> bool:
    res = await session.execute(
        select(ActivityEvent).where(
            ActivityEvent.person_id == person.id,
            ActivityEvent.event_type.in_(("pull_request_opened", "pull_request_merged")),
            ActivityEvent.occurred_at < before,
        )
    )
    for ev in res.scalars().all():
        if event_is_external(ev, person.github_username):
            return True
    return False


async def compute_since_items(
    session: AsyncSession,
    owner: Owner,
    *,
    since: datetime,
    limit: int = HIGHLIGHTS_LIMIT,
) -> list[dict]:
    res = await session.execute(
        select(Connection)
        .options(selectinload(Connection.person))
        .where(Connection.owner_id == owner.id)
    )
    connections = list(res.scalars().all())
    by_person = {c.person_id: c for c in connections}
    person_ids = list(by_person)
    if not person_ids:
        return []

    ev_res = await session.execute(
        select(ActivityEvent)
        .where(
            ActivityEvent.person_id.in_(person_ids),
            ActivityEvent.occurred_at > since,
        )
        .order_by(ActivityEvent.significance_score.desc(), ActivityEvent.occurred_at.desc())
    )
    events = list(ev_res.scalars().all())

    candidates: list[dict] = []

    for ev in events:
        conn = by_person.get(ev.person_id)
        if not conn:
            continue
        person = conn.person
        if owner.person_id and person.id == owner.person_id:
            continue
        is_close = conn.is_close
        external = event_is_external(ev, person.github_username) and ev.event_type in (
            "pull_request_opened",
            "pull_request_merged",
        )
        first_ext = False
        if external:
            first_ext = not await _had_external_pr_before(session, person, ev.occurred_at)

        name = display_name(person)
        verb = EVENT_LABELS.get(ev.event_type, ev.event_type.replace("_", " "))
        repo = ev.repo_full_name or "a repository"

        if first_ext:
            kind = "first_external"
            headline = f"{name} merged a first tracked PR to an external repo" if ev.event_type == "pull_request_merged" else f"{name} opened a first tracked PR to an external repo"
            reason = ("Close circle · " if is_close else "") + "First tracked contribution to an external project"
            rank = rank_score(
                significance=ev.significance_score,
                is_close=is_close,
                first_external=True,
                kind=kind,
            )
        elif ev.significance_score >= HIGH_SIGNIFICANCE_MIN:
            kind = "high_significance"
            headline = f"{name} {verb} on {repo}"
            reason = ("Close circle · " if is_close else "") + "Meaningful public GitHub activity"
            rank = rank_score(
                significance=ev.significance_score,
                is_close=is_close,
                kind=kind,
            )
        else:
            continue

        candidates.append(
            _item(
                item_id=f"event:{ev.id}",
                kind=kind,
                headline=headline,
                reason=reason,
                person_id=person.id,
                event_ids=[ev.id],
                person=person,
                rank=rank,
            )
        )

    pt_res = await session.execute(
        select(PersonTechnology, Technology, Person)
        .join(Technology, Technology.id == PersonTechnology.technology_id)
        .join(Person, Person.id == PersonTechnology.person_id)
        .where(
            PersonTechnology.person_id.in_(person_ids),
            PersonTechnology.first_seen_at.is_not(None),
            PersonTechnology.first_seen_at > since,
        )
    )
    for pt, tech, person in pt_res.all():
        conn = by_person.get(person.id)
        if not conn or (owner.person_id and person.id == owner.person_id):
            continue
        kind = "tech_novelty"
        rank = rank_score(
            significance=0,
            is_close=conn.is_close,
            tech_first_seen=True,
            kind=kind,
        )
        candidates.append(
            _item(
                item_id=f"tech:{person.id}:{tech.name}",
                kind=kind,
                headline=f"{display_name(person)}'s first tracked {tech.name} week",
                reason=("Close circle · " if conn.is_close else "") + "First tracked appearance of this technology",
                person_id=person.id,
                event_ids=[],
                person=person,
                rank=rank,
                extra={"tech": tech.name},
            )
        )

    try:
        facts = await compute_network_facts(session, owner.id)
        close_ids = {c.person_id for c in connections if c.is_close}
        for rising in facts.get("rising") or []:
            if rising.get("this_week_people", 0) < 3:
                continue
            person_ids_for_tech = []
            for row in facts.get("tech_this_week") or []:
                if row["name"] == rising["name"]:
                    person_ids_for_tech = row.get("person_ids") or []
                    break
            if close_ids.isdisjoint(set(person_ids_for_tech)):
                continue
            kind = "network_cluster"
            rank = rank_score(significance=0, is_close=True, kind=kind)
            candidates.append(
                _item(
                    item_id=f"cluster:{rising['name']}",
                    kind=kind,
                    headline=f"{rising['name']} is showing up across your network this week",
                    reason=f"{rising['this_week_people']} people, including someone in your close circle",
                    person_id=None,
                    event_ids=[],
                    person=None,
                    rank=rank,
                    extra={"tech": rising["name"], "href": f"/network?tech={rising['name']}"},
                )
            )
    except Exception:
        facts = {}

    # Prefer unique persons / clusters; keep highest rank per id
    by_id: dict[str, dict] = {}
    for item in candidates:
        existing = by_id.get(item["id"])
        if existing is None or item["rank"] > existing["rank"]:
            by_id[item["id"]] = item
    ranked = sorted(by_id.values(), key=lambda i: i["rank"], reverse=True)

    selected = [i for i in ranked if i["kind"] != "close_quiet"][:limit]

    if len(selected) < limit:
        quiet_slots = min(CLOSE_QUIET_MAX_SLOTS, limit - len(selected))
        lookback = since - timedelta(days=14)
        for conn in connections:
            if quiet_slots <= 0:
                break
            if not conn.is_close:
                continue
            if owner.person_id and conn.person_id == owner.person_id:
                continue
            recent = [e for e in events if e.person_id == conn.person_id]
            if recent:
                continue
            prior = await session.execute(
                select(ActivityEvent.id)
                .where(
                    ActivityEvent.person_id == conn.person_id,
                    ActivityEvent.occurred_at >= lookback,
                    ActivityEvent.occurred_at <= since,
                )
                .limit(1)
            )
            if prior.scalar_one_or_none() is None:
                continue
            person = conn.person
            selected.append(
                _item(
                    item_id=f"quiet:{person.id}",
                    kind="close_quiet",
                    headline=f"{display_name(person)} in your close circle has been quiet",
                    reason="Close circle connection with prior activity and no recent tracked events",
                    person_id=person.id,
                    event_ids=[],
                    person=person,
                    rank=rank_score(significance=0, is_close=True, kind="close_quiet"),
                )
            )
            quiet_slots -= 1

    for item in selected:
        item.pop("rank", None)
    return selected[:limit]


def default_since(acked_at: datetime | None) -> datetime:
    if acked_at is not None:
        return acked_at
    return datetime.now(timezone.utc) - timedelta(days=7)
