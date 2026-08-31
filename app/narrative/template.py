from collections import Counter
from typing import Any


_LABELS = {
    "push": "push",
    "pull_request_opened": "opened a pull request",
    "pull_request_merged": "merged a pull request",
    "pull_request_reviewed": "reviewed a pull request",
    "issue_opened": "opened an issue",
    "release_published": "published a release",
    "fork": "forked a repo",
    "repository_created": "created a repository",
    "tag_created": "created a tag",
}


def _name(person: dict[str, Any]) -> str:
    return person.get("display_name") or person["github_username"]


def _event_type(event: dict[str, Any]) -> str:
    return event.get("event_type") or event.get("type") or ""


def _repo(event: dict[str, Any]) -> str | None:
    return event.get("repo_full_name") or event.get("repo")


def template_narrative(
    person: dict[str, Any],
    events: list[dict[str, Any]],
    technologies: list[dict[str, Any]] | None = None,
) -> tuple[str, list[int], str]:
    """Grounded one-paragraph summary from stored events. Never claims 'nothing happened' if events exist."""
    if not events:
        return (
            f"{_name(person)} had no tracked public GitHub activity in this window.",
            [],
            "template-empty",
        )

    counts = Counter(_event_type(e) for e in events if _event_type(e))
    repos = [r for e in events if (r := _repo(e))]
    top_repos = [name for name, _ in Counter(repos).most_common(3)]
    event_ids = [e["id"] for e in events if e.get("id") is not None]

    notable = []
    for key, phrase in (
        ("pull_request_merged", "merged {n} PR(s)"),
        ("pull_request_opened", "opened {n} PR(s)"),
        ("pull_request_reviewed", "reviewed {n} PR(s)"),
        ("release_published", "published {n} release(s)"),
        ("repository_created", "created {n} repo(s)"),
        ("issue_opened", "opened {n} issue(s)"),
        ("fork", "forked {n} repo(s)"),
        ("push", "pushed {n} time(s)"),
    ):
        n = counts.get(key, 0)
        if n:
            notable.append(phrase.format(n=n))

    if not notable:
        notable.append(f"had {len(events)} tracked event(s)")

    text = f"{_name(person)} " + ", ".join(notable)
    if top_repos:
        text += f" — mainly in {', '.join(top_repos)}"
    tech_names = [t["name"] for t in (technologies or [])[:4] if t.get("name")]
    if tech_names:
        text += f" ({', '.join(tech_names)})"
    text += "."
    return text, event_ids[:20], "template"


def activity_digest(events: list[dict[str, Any]]) -> dict[str, Any]:
    repos = [r for e in events if (r := _repo(e))]
    return {
        "event_count": len(events),
        "significance_total": sum(int(e.get("significance_score") or 0) for e in events),
        "top_repos": [name for name, _ in Counter(repos).most_common(3)],
        "counts": dict(Counter(_event_type(e) for e in events if _event_type(e))),
    }
