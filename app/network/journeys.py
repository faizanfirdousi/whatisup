"""Developer journey milestones from stored events — observational, not gamified."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any

from app.scoring.technology import extract_technologies


def _event_type(event: Any) -> str:
    if isinstance(event, dict):
        return event.get("event_type") or ""
    return event.event_type or ""


def _event_repo(event: Any) -> str:
    if isinstance(event, dict):
        return event.get("repo_full_name") or ""
    return event.repo_full_name or ""


def _event_at(event: Any) -> datetime | None:
    occurred = getattr(event, "occurred_at", None)
    if occurred is None and isinstance(event, dict):
        occurred = event.get("occurred_at")
    if isinstance(occurred, str):
        return datetime.fromisoformat(occurred)
    return occurred


def _is_external(event: Any, github_username: str) -> bool:
    meta = getattr(event, "metadata_", None)
    if meta is None and isinstance(event, dict):
        meta = event.get("metadata_") or event.get("metadata") or {}
    else:
        meta = meta or {}
    if "is_external" in meta:
        return bool(meta["is_external"])
    repo = _event_repo(event)
    if "/" not in repo:
        return False
    return repo.split("/", 1)[0].lower() != (github_username or "").lower()


def _month_label(d: date) -> str:
    return d.strftime("%B")


def detect_milestones(
    events: list[Any],
    *,
    github_username: str,
    tech_first_seen: dict[str, date] | None = None,
) -> list[dict[str, Any]]:
    """Return ordered milestone dicts grounded in event history."""
    if not events:
        return []

    tech_first_seen = tech_first_seen or {}
    sorted_events = sorted(events, key=lambda e: _event_at(e) or datetime.min)
    milestones: list[dict[str, Any]] = []

    first_repo = next((e for e in sorted_events if _event_type(e) == "repository_created"), None)
    if first_repo:
        at = _event_at(first_repo)
        milestones.append(
            {
                "kind": "first_repository",
                "label": "First repository",
                "detail": _event_repo(first_repo) or "Created a tracked repository",
                "occurred_at": at.isoformat() if at else None,
            }
        )

    external_prs = [
        e
        for e in sorted_events
        if _event_type(e) in ("pull_request_opened", "pull_request_merged")
        and _is_external(e, github_username)
    ]
    if external_prs:
        first_ext = external_prs[0]
        at = _event_at(first_ext)
        milestones.append(
            {
                "kind": "first_external_pr",
                "label": "First external contribution",
                "detail": f"Contributed to {_event_repo(first_ext) or 'an external project'}",
                "occurred_at": at.isoformat() if at else None,
            }
        )

    first_release = next((e for e in sorted_events if _event_type(e) == "release_published"), None)
    if first_release:
        at = _event_at(first_release)
        milestones.append(
            {
                "kind": "first_release",
                "label": "First release",
                "detail": _event_repo(first_release) or "Published a release",
                "occurred_at": at.isoformat() if at else None,
            }
        )

    for tech, first in sorted(tech_first_seen.items(), key=lambda item: item[1]):
        milestones.append(
            {
                "kind": "first_technology",
                "label": f"First tracked {tech}",
                "detail": f"Started appearing in {tech}-related work",
                "occurred_at": first.isoformat() if isinstance(first, date) else None,
            }
        )

    # Recurring tech: seen in 3+ distinct months
    tech_months: dict[str, set[str]] = defaultdict(set)
    for event in sorted_events:
        at = _event_at(event)
        if not at:
            continue
        month_key = at.strftime("%Y-%m")
        for tech in extract_technologies(getattr(event, "metadata_", None) or event.get("metadata_", {}) if isinstance(event, dict) else event.metadata_ or {}):
            tech_months[tech["name"]].add(month_key)
    for tech, months in tech_months.items():
        if len(months) >= 3 and tech not in {m["detail"] for m in milestones if m["kind"] == "first_technology"}:
            milestones.append(
                {
                    "kind": "recurring_technology",
                    "label": f"{tech.title()} became recurring",
                    "detail": f"Active across {len(months)} months of tracked work",
                    "occurred_at": None,
                }
            )

    return milestones[:8]


def build_monthly_phases(
    events: list[Any],
    *,
    github_username: str,
    limit_months: int = 4,
) -> list[dict[str, Any]]:
    """Monthly narrative slices for a person's trajectory."""
    by_month: dict[str, list[Any]] = defaultdict(list)
    for event in events:
        at = _event_at(event)
        if not at:
            continue
        by_month[at.strftime("%Y-%m")].append(event)

    phases: list[dict[str, Any]] = []
    for month_key in sorted(by_month.keys(), reverse=True)[:limit_months]:
        month_events = by_month[month_key]
        at = _event_at(month_events[0])
        if not at:
            continue

        techs: Counter[str] = Counter()
        types: Counter[str] = Counter()
        repos: Counter[str] = Counter()
        for event in month_events:
            types[_event_type(event)] += 1
            repo = _event_repo(event)
            if repo:
                repos[repo.split("/")[-1]] += 1
            for tech in extract_technologies(
                event.get("metadata_", {}) if isinstance(event, dict) else event.metadata_ or {}
            ):
                techs[tech["name"]] += 1

        top_tech = techs.most_common(1)[0][0] if techs else None
        top_repo = repos.most_common(1)[0][0] if repos else None
        external = any(
            _is_external(e, github_username)
            for e in month_events
            if _event_type(e) in ("pull_request_opened", "pull_request_merged")
        )

        if external:
            summary = f"Contributed to external open-source projects"
            if top_tech:
                summary += f", mainly around {top_tech}"
        elif types.get("release_published"):
            summary = f"Shipped releases"
            if top_repo:
                summary += f" in {top_repo}"
        elif types.get("repository_created"):
            summary = "Started new projects"
            if top_tech:
                summary += f" with {top_tech}"
        elif top_tech and top_repo:
            summary = f"Mostly {top_tech} work in {top_repo}"
        elif top_tech:
            summary = f"Mostly working on {top_tech} projects"
        elif top_repo:
            summary = f"Focused on {top_repo}"
        else:
            summary = "Had tracked public GitHub activity"

        phases.append(
            {
                "month": _month_label(at.date()),
                "month_key": month_key,
                "summary": summary,
                "technologies": [name for name, _ in techs.most_common(3)],
            }
        )

    return phases


def journey_hook(phases: list[dict[str, Any]]) -> str | None:
    """One-line trajectory for cards when full journey is too much."""
    if len(phases) < 2:
        return None
    latest = phases[0]
    prior = phases[1]
    latest_tech = (latest.get("technologies") or [None])[0]
    prior_tech = (prior.get("technologies") or [None])[0]
    if latest_tech and prior_tech and latest_tech != prior_tech:
        return f"From {prior_tech} toward {latest_tech} over recent months"
    if latest.get("summary") and prior.get("summary") and latest["summary"] != prior["summary"]:
        return f"Shifted from {prior['summary'].lower()} to {latest['summary'].lower()}"
    return None
