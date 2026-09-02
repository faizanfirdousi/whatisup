from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity_event import ActivityEvent
from app.models.connection import Connection
from app.models.owner import Owner
from app.models.person import Person
from app.models.technology import PersonTechnology, Technology
from app.network.thresholds import (
    DECLINING_PRIOR_MIN,
    NEW_IN_NETWORK_MIN_PEOPLE,
    PRIOR_WINDOW_DAYS,
    RISING_MIN_PEOPLE,
    RISING_MULTIPLIER,
)
from app.pipeline import current_week_bounds
from app.scoring.technology import extract_technologies


VALID_PERIODS = {"2d", "7d", "14d", "30d", "this_week"}


def get_period_bounds(period: str, today: date | None = None) -> tuple[date, date, datetime, datetime]:
    if period not in VALID_PERIODS:
        period = "2d"
    today = today or datetime.now(timezone.utc).date()
    if period == "this_week":
        return current_week_bounds(today)
    
    days = int(period[:-1])
            
    end_date = today
    start_date = end_date - timedelta(days=days - 1)
    
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
    return start_date, end_date, start_dt, end_dt



def event_is_external(event: Any, github_username: str) -> bool:
    meta = getattr(event, "metadata_", None)
    if meta is None and isinstance(event, dict):
        meta = event.get("metadata_") or event.get("metadata") or {}
    else:
        meta = meta or {}
    if "is_external" in meta:
        return bool(meta["is_external"])

    repo = getattr(event, "repo_full_name", None)
    if repo is None and isinstance(event, dict):
        repo = event.get("repo_full_name") or ""
    repo = repo or ""
    if "/" not in repo:
        return False
    return repo.split("/", 1)[0].lower() != (github_username or "").lower()


def _event_type(event: Any) -> str:
    if isinstance(event, dict):
        return event.get("event_type") or ""
    return event.event_type or ""


def _event_id(event: Any) -> int | None:
    if isinstance(event, dict):
        return event.get("id")
    return getattr(event, "id", None)


def _event_person_id(event: Any) -> int:
    if isinstance(event, dict):
        return event["person_id"]
    return event.person_id


def _event_repo(event: Any) -> str:
    if isinstance(event, dict):
        return event.get("repo_full_name") or ""
    return event.repo_full_name or ""


def _event_meta(event: Any) -> dict:
    if isinstance(event, dict):
        return event.get("metadata_") or event.get("metadata") or {}
    return event.metadata_ or {}


def _is_pr(event: Any) -> bool:
    return _event_type(event) in ("pull_request_opened", "pull_request_merged")


def all_person_ids_from_facts(facts: dict) -> set[int]:
    ids: set[int] = set(facts.get("active_person_ids") or [])
    ids.update(facts.get("quiet_close_person_ids") or [])
    for item in facts.get("tech_this_week") or []:
        ids.update(item.get("person_ids") or [])
        ids.update(item.get("new_to_person_ids") or [])
    for item in facts.get("new_in_network") or []:
        ids.update(item.get("person_ids") or [])
    for item in facts.get("first_external_oss") or []:
        if item.get("person_id"):
            ids.add(item["person_id"])
    return ids


def all_tech_names_from_facts(facts: dict) -> set[str]:
    names: set[str] = set()
    for key in ("tech_this_week", "tech_prior_window", "rising", "new_in_network", "declining"):
        for item in facts.get(key) or []:
            if item.get("name"):
                names.add(item["name"].lower())
    return names


def facts_from_loaded(
    *,
    week_start: date,
    week_end: date,
    owner_person_id: int | None,
    connections: list[dict],
    week_events: list[Any],
    prior_events: list[Any],
    usernames: dict[int, str],
    tech_this_week: dict[str, set[int]],
    first_seen_by_person_tech: dict[tuple[int, str], date],
    tech_seen_before_week: set[str],
    period_days: int = 7,
) -> dict:
    """Pure assembly used by tests and by the SQL loader."""
    follow_ids = [
        c["person_id"] for c in connections if c["person_id"] != owner_person_id
    ]
    follow_set = set(follow_ids)
    close_ids = [c["person_id"] for c in connections if c["is_close"] and c["person_id"] != owner_person_id]

    events_by_person: dict[int, list] = defaultdict(list)
    type_counts: Counter[str] = Counter()
    repos_by_person: dict[int, set[str]] = defaultdict(set)
    for ev in week_events:
        pid = _event_person_id(ev)
        if pid not in follow_set and pid != owner_person_id:
            continue
        if pid in follow_set:
            events_by_person[pid].append(ev)
            type_counts[_event_type(ev)] += 1
            repo = _event_repo(ev)
            if repo:
                repos_by_person[pid].add(repo)

    active_person_ids = sorted(pid for pid in follow_ids if events_by_person.get(pid))
    quiet_close = sorted(pid for pid in close_ids if not events_by_person.get(pid))

    # Calculate shared repos
    repo_to_people: dict[str, set[int]] = defaultdict(set)
    for pid, repos in repos_by_person.items():
        for repo in repos:
            repo_to_people[repo].add(pid)
            
    shared_repos = []
    for repo, pids in repo_to_people.items():
        if len(pids) >= 2:
            shared_repos.append({
                "repo": repo,
                "people_count": len(pids),
                "person_ids": sorted(list(pids))
            })
    shared_repos.sort(key=lambda x: x["people_count"], reverse=True)

    prior_people_by_tech: dict[str, set[int]] = defaultdict(set)
    prior_events_by_person: dict[int, list] = defaultdict(list)
    
    # We only care about events in the equivalent preceding period for activity direction
    # compute_network_facts passes all prior_events (up to PRIOR_WINDOW_DAYS).
    # We'll filter for the immediate prior period manually.
    for ev in prior_events:
        pid = _event_person_id(ev)
        if pid not in follow_set:
            continue
        
        # Tech uses the whole prior window
        for t in extract_technologies(_event_meta(ev)):
            prior_people_by_tech[t["name"]].add(pid)
            
        # Activity direction uses just the immediate preceding period
        occurred = getattr(ev, "occurred_at", None)
        if isinstance(ev, dict) and occurred is None:
            occurred = ev.get("occurred_at")

        in_prior_period = True
        if occurred:
            if isinstance(occurred, str):
                occurred = datetime.fromisoformat(occurred)
            start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)
            in_prior_period = occurred >= start_dt - timedelta(days=period_days)
        if in_prior_period:
            prior_events_by_person[pid].append(ev)

    activity_direction = {}
    people_by_activity_level = {"more_active": [], "steady": [], "quiet": []}

    for pid in follow_ids:
        cur_events = len(events_by_person.get(pid, []))
        prior_events_count = len(prior_events_by_person.get(pid, []))
        prior_repos = {_event_repo(e) for e in prior_events_by_person.get(pid, []) if _event_repo(e)}
        new_repos = sorted(repos_by_person.get(pid, set()) - prior_repos)

        if prior_events_count == 0:
            change_pct = 100 if cur_events else 0
        else:
            change_pct = round(((cur_events - prior_events_count) / prior_events_count) * 100)

        if cur_events == 0 and prior_events_count == 0:
            direction = "steady"
            level = "quiet"
        elif cur_events == 0:
            direction = "down"
            level = "quiet"
        elif cur_events > prior_events_count * 1.5:
            direction = "up"
            level = "more_active"
        elif cur_events < prior_events_count * 0.5:
            direction = "down"
            level = "steady"
        else:
            direction = "steady"
            level = "steady"

        activity_direction[pid] = {
            "direction": direction,
            "this_period_events": cur_events,
            "prior_period_events": prior_events_count,
            "change_pct": change_pct,
            "new_repos": new_repos[:5],
        }
        people_by_activity_level[level].append(pid)

    # Merge explicit prior tech map if provided via tech_this_week sibling
    tech_rows = []
    for name, person_ids in sorted(tech_this_week.items()):
        pids = sorted(pid for pid in person_ids if pid in follow_set)
        if not pids:
            continue
        new_to = [
            pid
            for pid in pids
            if first_seen_by_person_tech.get((pid, name), week_start) >= week_start
        ]
        tech_rows.append({"name": name, "person_ids": pids, "new_to_person_ids": new_to})

    prior_rows = []
    all_tech_names = set(tech_this_week) | set(prior_people_by_tech)
    for name in sorted(all_tech_names):
        prior_count = len(prior_people_by_tech.get(name, set()))
        prior_rows.append(
            {"name": name, "person_count": prior_count, "window_days": PRIOR_WINDOW_DAYS}
        )

    rising = []
    weeks_in_prior = PRIOR_WINDOW_DAYS / 7
    for name, pids in tech_this_week.items():
        this_week_people = len([p for p in pids if p in follow_set])
        prior_people = len(prior_people_by_tech.get(name, set()))
        prior_avg = prior_people / weeks_in_prior
        if this_week_people >= RISING_MIN_PEOPLE and this_week_people >= RISING_MULTIPLIER * max(prior_avg, 0):
            rising.append(
                {
                    "name": name,
                    "this_week_people": this_week_people,
                    "prior_4w_avg_people": round(prior_avg, 2),
                }
            )

    new_in_network = []
    for name, pids in tech_this_week.items():
        followed = [p for p in pids if p in follow_set]
        if len(followed) < NEW_IN_NETWORK_MIN_PEOPLE:
            continue
        all_first_this_week = all(
            first_seen_by_person_tech.get((pid, name), week_start) >= week_start for pid in followed
        )
        if all_first_this_week and name not in tech_seen_before_week:
            new_in_network.append({"name": name, "person_ids": sorted(followed)})

    declining = []
    for name, people in prior_people_by_tech.items():
        this_week_people = len([p for p in tech_this_week.get(name, set()) if p in follow_set])
        if this_week_people == 0 and len(people) >= DECLINING_PRIOR_MIN:
            declining.append(
                {
                    "name": name,
                    "this_week_people": 0,
                    "prior_4w_people": len(people),
                }
            )

    first_external = []
    # First external PR in tracked history whose first occurrence is this week:
    # caller should only pass week_events that are the person's first external PR.
    for ev in week_events:
        pid = _event_person_id(ev)
        if pid not in follow_set or not _is_pr(ev):
            continue
        username = usernames.get(pid, "")
        if not event_is_external(ev, username):
            continue
        first_external.append(
            {
                "person_id": pid,
                "event_id": _event_id(ev),
                "repo": _event_repo(ev),
            }
        )

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "network_size": len(follow_ids),
        "close_circle_size": len(close_ids),
        "active_person_ids": active_person_ids,
        "quiet_close_person_ids": quiet_close,
        "tech_this_week": tech_rows,
        "tech_prior_window": prior_rows,
        "rising": rising,
        "new_in_network": new_in_network,
        "declining": declining,
        "first_external_oss": first_external,
        "event_type_counts": dict(type_counts),
        "shared_repos": shared_repos,
        "activity_direction": activity_direction,
        "people_by_activity_level": people_by_activity_level,
    }


async def compute_network_facts(
    session: AsyncSession, owner_id: int, today: date | None = None, period: str = "2d"
) -> dict:
    owner = await session.get(Owner, owner_id)
    week_start, week_end, start_dt, end_dt = get_period_bounds(period, today)
    period_days = (week_end - week_start).days + 1
    prior_start = start_dt - timedelta(days=max(PRIOR_WINDOW_DAYS, period_days))

    res = await session.execute(
        select(Connection)
        .options(selectinload(Connection.person))
        .where(Connection.owner_id == owner_id)
    )
    conns = list(res.scalars().all())
    connections = [{"person_id": c.person_id, "is_close": c.is_close} for c in conns]
    usernames = {c.person_id: c.person.github_username for c in conns}
    person_ids = [c.person_id for c in conns]
    owner_person_id = owner.person_id if owner else None

    week_events: list[ActivityEvent] = []
    prior_events: list[ActivityEvent] = []
    if person_ids:
        from sqlalchemy.orm import defer

        ev_res = await session.execute(
            select(ActivityEvent)
            .options(defer(ActivityEvent.raw_payload))
            .where(
                ActivityEvent.person_id.in_(person_ids),
                ActivityEvent.occurred_at >= prior_start,
                ActivityEvent.occurred_at <= end_dt,
            )
        )
        for ev in ev_res.scalars().all():
            if start_dt <= ev.occurred_at <= end_dt:
                week_events.append(ev)
            elif prior_start <= ev.occurred_at < start_dt:
                prior_events.append(ev)

    tech_this_week: dict[str, set[int]] = defaultdict(set)
    for ev in week_events:
        for t in extract_technologies(ev.metadata_ or {}):
            tech_this_week[t["name"]].add(ev.person_id)

    first_seen_by_person_tech: dict[tuple[int, str], date] = {}
    tech_seen_before_week: set[str] = set()
    if person_ids:
        pt_res = await session.execute(
            select(PersonTechnology, Technology.name)
            .join(Technology, Technology.id == PersonTechnology.technology_id)
            .where(PersonTechnology.person_id.in_(person_ids))
        )
        for pt, name in pt_res.all():
            first = pt.first_seen_at or pt.last_seen_at
            first_date = first.date() if isinstance(first, datetime) else first
            first_seen_by_person_tech[(pt.person_id, name)] = first_date
            if first_date < week_start:
                tech_seen_before_week.add(name)
            if start_dt <= pt.last_seen_at <= end_dt:
                tech_this_week[name].add(pt.person_id)

    pr_types = ("pull_request_opened", "pull_request_merged")
    pr_people = {ev.person_id for ev in week_events if ev.event_type in pr_types}
    earlier_external: set[int] = set()
    if pr_people:
        hist = await session.execute(
            select(
                ActivityEvent.person_id,
                ActivityEvent.repo_full_name,
                ActivityEvent.metadata_,
                Person.github_username,
            )
            .join(Person, Person.id == ActivityEvent.person_id)
            .where(
                ActivityEvent.person_id.in_(pr_people),
                ActivityEvent.event_type.in_(pr_types),
                ActivityEvent.occurred_at < start_dt,
            )
        )

        class _Hist:
            __slots__ = ("person_id", "repo_full_name", "metadata_")

            def __init__(self, person_id, repo_full_name, metadata_):
                self.person_id = person_id
                self.repo_full_name = repo_full_name
                self.metadata_ = metadata_

        for person_id, repo, meta, username in hist.all():
            if person_id in earlier_external:
                continue
            ev = _Hist(person_id, repo, meta)
            if event_is_external(ev, username):
                earlier_external.add(person_id)

    first_week_external = []
    seen_person: set[int] = set()
    for ev in sorted(week_events, key=lambda e: e.occurred_at):
        if ev.person_id in earlier_external or ev.person_id in seen_person:
            continue
        if ev.event_type not in pr_types:
            continue
        if event_is_external(ev, usernames.get(ev.person_id, "")):
            first_week_external.append(ev)
            seen_person.add(ev.person_id)

    facts = facts_from_loaded(
        week_start=week_start,
        week_end=week_end,
        owner_person_id=owner_person_id,
        connections=connections,
        week_events=week_events,
        prior_events=prior_events,
        usernames=usernames,
        tech_this_week=tech_this_week,
        first_seen_by_person_tech=first_seen_by_person_tech,
        tech_seen_before_week=tech_seen_before_week,
        period_days=period_days,
    )
    facts["first_external_oss"] = [
        {"person_id": ev.person_id, "event_id": ev.id, "repo": ev.repo_full_name or ""}
        for ev in first_week_external
        if ev.person_id != owner_person_id
    ]
    return facts
