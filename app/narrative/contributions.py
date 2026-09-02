"""Ground person insights in what they actually did, not just the stack."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.github.work_signals import extract_work_signals

# Distinctive first. Generic "contribution" is last-resort.
_KIND_PRIORITY = ("tests", "release", "reviews", "docs", "ci", "infra", "fix", "refactor")

_KIND_PHRASE = {
    "tests": "writing tests",
    "docs": "updating docs",
    "ci": "working on CI",
    "infra": "working on infrastructure",
    "fix": "fixing bugs",
    "refactor": "refactoring",
    "reviews": "reviewing pull requests",
    "release": "shipping a release",
}

_KIND_HEADLINE = {
    "tests": "Wrote tests",
    "docs": "Updated docs",
    "ci": "Worked on CI",
    "infra": "Worked on infrastructure",
    "fix": "Fixed bugs",
    "refactor": "Refactored code",
    "reviews": "Reviewed pull requests",
    "release": "Shipped a release",
}

_KIND_FOCUS = {
    "tests": "testing",
    "docs": "documentation",
    "ci": "ci/cd",
    "infra": "infrastructure",
    "fix": "bugfixes",
    "refactor": "refactoring",
    "reviews": "code review",
    "release": "release",
}

_TYPE_LABEL = {
    "push": "pushed commits",
    "pull_request_opened": "opened a pull request",
    "pull_request_merged": "merged a pull request",
    "pull_request_reviewed": "reviewed a pull request",
    "issue_opened": "opened an issue",
    "release_published": "published a release",
    "fork": "forked a repo",
    "repository_created": "created a repository",
    "tag_created": "created a tag",
}


def _event_type(event: dict[str, Any]) -> str:
    return event.get("event_type") or event.get("type") or ""


def _repo(event: dict[str, Any]) -> str | None:
    return event.get("repo_full_name") or event.get("repo")


def _meta(event: dict[str, Any]) -> dict[str, Any]:
    return event.get("metadata_") or event.get("metadata") or {}


def _raw(event: dict[str, Any]) -> dict[str, Any]:
    return event.get("raw_payload") or {}


def work_from_event(event: dict[str, Any]) -> dict[str, Any]:
    """Prefer stored metadata; fall back to the original GitHub payload."""
    meta = _meta(event)
    signals = {
        "titles": list(meta.get("titles") or []),
        "commit_subjects": list(meta.get("commit_subjects") or []),
        "work_kinds": list(meta.get("work_kinds") or []),
    }
    if not signals["titles"] and not signals["commit_subjects"]:
        extracted = extract_work_signals(_raw(event))
        for key in ("titles", "commit_subjects", "work_kinds"):
            if extracted.get(key):
                signals[key] = list(extracted[key])

    event_type = _event_type(event)
    kinds = list(signals["work_kinds"])
    if event_type == "pull_request_reviewed" and "reviews" not in kinds:
        kinds.append("reviews")
    if event_type == "release_published" and "release" not in kinds:
        kinds.append("release")
    signals["work_kinds"] = kinds
    return signals


def _is_external(event: dict[str, Any], person: dict[str, Any]) -> bool:
    meta = _meta(event)
    if "is_external" in meta:
        return bool(meta["is_external"])
    repo = _repo(event) or ""
    if "/" not in repo:
        return False
    username = person.get("github_username") or ""
    return repo.split("/", 1)[0].lower() != username.lower()


def pick_primary_kind(kinds: list[str]) -> str | None:
    for kind in _KIND_PRIORITY:
        if kind in kinds:
            return kind
    return kinds[0] if kinds else None


def kind_phrase(kinds: list[str]) -> str | None:
    primary = pick_primary_kind(kinds)
    if not primary:
        return None
    return _KIND_PHRASE.get(primary)


def kind_headline(kinds: list[str]) -> str | None:
    primary = pick_primary_kind(kinds)
    if not primary:
        return None
    return _KIND_HEADLINE.get(primary)


def kind_focus(kinds: list[str]) -> str | None:
    primary = pick_primary_kind(kinds)
    if not primary:
        return None
    return _KIND_FOCUS.get(primary)


def build_contribution_digest(
    person: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """High-level, evidence-backed picture of what this person did."""
    by_repo: dict[str, dict[str, Any]] = {}
    all_kinds: list[str] = []
    points: list[str] = []

    for event in events:
        repo = _repo(event)
        if not repo:
            continue
        work = work_from_event(event)
        meta = _meta(event)
        bucket = by_repo.setdefault(
            repo,
            {
                "repo": repo,
                "external": False,
                "actions": [],
                "kinds": [],
                "titles": [],
                "commit_subjects": [],
                "description": meta.get("description"),
                "language": meta.get("language"),
            },
        )
        if _is_external(event, person):
            bucket["external"] = True
        if meta.get("description") and not bucket.get("description"):
            bucket["description"] = meta.get("description")
        if meta.get("language") and not bucket.get("language"):
            bucket["language"] = meta.get("language")

        action = _TYPE_LABEL.get(_event_type(event))
        if action and action not in bucket["actions"]:
            bucket["actions"].append(action)
        for kind in work["work_kinds"]:
            if kind not in bucket["kinds"]:
                bucket["kinds"].append(kind)
            all_kinds.append(kind)
        for title in work["titles"]:
            if title not in bucket["titles"]:
                bucket["titles"].append(title)
        for subject in work["commit_subjects"]:
            if subject not in bucket["commit_subjects"]:
                bucket["commit_subjects"].append(subject)

    repos = sorted(
        by_repo.values(),
        key=lambda row: (not row["external"], -len(row["titles"]), -len(row["actions"])),
    )

    for row in repos[:5]:
        short = row["repo"].split("/")[-1] if "/" in row["repo"] else row["repo"]
        where = f"{'external repo ' if row['external'] else ''}{row['repo']}"
        phrase = kind_phrase(row["kinds"])
        action = row["actions"][0] if row["actions"] else "was active"
        title = row["titles"][0] if row["titles"] else None
        if phrase and title:
            points.append(f"{action.capitalize()} in {where} by {phrase} (\"{title}\").")
        elif phrase:
            points.append(f"{action.capitalize()} in {where} by {phrase}.")
        elif title:
            points.append(f"{action.capitalize()} in {where}: \"{title}\".")
        else:
            points.append(f"{action.capitalize()} in {where}.")
        if row.get("description"):
            points.append(f"{short} is described as: {str(row['description'])[:160]}")

    ranked_kinds = [k for k, _ in Counter(all_kinds).most_common()]
    ranked_kinds = [k for k in _KIND_PRIORITY if k in ranked_kinds] + [
        k for k in ranked_kinds if k not in _KIND_PRIORITY
    ]

    return {
        "work_kinds": ranked_kinds,
        "primary_kind": pick_primary_kind(ranked_kinds),
        "repos": [
            {
                "repo": row["repo"],
                "external": row["external"],
                "actions": row["actions"][:4],
                "kinds": row["kinds"],
                "titles": row["titles"][:3],
                "commit_subjects": row["commit_subjects"][:3],
                "description": row.get("description"),
                "language": row.get("language"),
            }
            for row in repos[:6]
        ],
        "summary_points": points[:8],
    }
