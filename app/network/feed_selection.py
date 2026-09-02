"""Diverse feed selection — avoid flooding with the same signal type."""

from __future__ import annotations

from typing import Any, Callable

from app.scoring.canonical import canonical_key

PENALTY_SAME_ACTIVITY = 120
PENALTY_SAME_TECH = 50
PENALTY_SAME_REPO = 40
PENALTY_SAME_PERSON = 1000

# Reserved slots — at most one story per slot when candidates exist.
SLOT_FILTERS: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
    ("external_contribution", lambda s: s.get("activity_type") == "external_contribution"),
    ("release", lambda s: s.get("activity_type") == "release"),
    ("new_project", lambda s: s.get("activity_type") == "new_project"),
    ("tech_shift", lambda s: bool(s.get("is_tech_shift"))),
    (
        "personal_relevance",
        lambda s: bool(s.get("personal_note")) or (s.get("relevance") or 0) >= 18,
    ),
]


def repo_ecosystem(repos: list[str]) -> str | None:
    for repo in repos:
        if repo and "/" in repo:
            return repo.split("/", 1)[0].lower()
    return None


def primary_tech(technologies: list[str]) -> str | None:
    if not technologies:
        return None
    return canonical_key(technologies[0])


def _adjusted_score(story: dict[str, Any], selected: list[dict[str, Any]]) -> float:
    score = float(story.get("rank") or 0)
    for picked in selected:
        if story["person"]["id"] == picked["person"]["id"]:
            score -= PENALTY_SAME_PERSON
        if story.get("activity_type") == picked.get("activity_type"):
            score -= PENALTY_SAME_ACTIVITY
        if (
            story.get("primary_tech")
            and story.get("primary_tech") == picked.get("primary_tech")
        ):
            score -= PENALTY_SAME_TECH
        if (
            story.get("repo_ecosystem")
            and story.get("repo_ecosystem") == picked.get("repo_ecosystem")
        ):
            score -= PENALTY_SAME_REPO
    return score


def _pick_best(candidates: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    return max(candidates, key=lambda story: _adjusted_score(story, selected))


def select_diverse_stories(stories: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    """Pick a heterogeneous feed: one slot per story type, then MMR fill."""
    if not stories:
        return []

    pool = sorted(stories, key=lambda item: item.get("rank", 0), reverse=True)
    selected: list[dict[str, Any]] = []

    for _slot_name, matches in SLOT_FILTERS:
        if len(selected) >= limit:
            break
        candidates = [s for s in pool if s not in selected and matches(s)]
        best = _pick_best(candidates, selected)
        if best:
            selected.append(best)

    remaining = [s for s in pool if s not in selected]

    while len(selected) < limit and remaining:
        best = _pick_best(remaining, selected)
        if best is None:
            break
        selected.append(best)
        remaining.remove(best)

    return selected[:limit]
