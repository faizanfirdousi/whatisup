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

# Map event types to activity_type classification
_ACTIVITY_TYPE_PRIORITY = [
    ({"release_published"}, "release"),
    ({"repository_created"}, "new_project"),
    ({"pull_request_opened", "pull_request_merged"}, "external_contribution"),  # only if external
    ({"pull_request_opened", "pull_request_merged", "pull_request_reviewed"}, "deep_work"),
    ({"push"}, "routine"),
    ({"fork", "issue_opened"}, "exploration"),
]


def _name(person: dict[str, Any]) -> str:
    return person.get("display_name") or person["github_username"]


def _event_type(event: dict[str, Any]) -> str:
    return event.get("event_type") or event.get("type") or ""


def _repo(event: dict[str, Any]) -> str | None:
    return event.get("repo_full_name") or event.get("repo")


def _repo_short(repo: str) -> str:
    return repo.split("/")[-1] if "/" in repo else repo


def _is_external(event: dict[str, Any], person: dict[str, Any]) -> bool:
    """Check if event is on a repo not owned by the person."""
    meta = event.get("metadata_") or event.get("metadata") or {}
    if "is_external" in meta:
        return bool(meta["is_external"])
    repo = _repo(event) or ""
    if "/" not in repo:
        return False
    username = person.get("github_username") or ""
    return repo.split("/", 1)[0].lower() != username.lower()


def _determine_activity_type(events: list[dict[str, Any]], person: dict[str, Any]) -> str:
    """Classify the dominant activity type for this period."""
    types = set(_event_type(e) for e in events if _event_type(e))
    has_external = any(
        _is_external(e, person)
        for e in events
        if _event_type(e) in ("pull_request_opened", "pull_request_merged")
    )

    if "release_published" in types:
        return "release"
    if "repository_created" in types:
        return "new_project"
    if has_external:
        return "external_contribution"
    if types & {"pull_request_opened", "pull_request_merged", "pull_request_reviewed"}:
        return "deep_work"
    if types & {"fork", "issue_opened"}:
        return "exploration"
    return "routine"


def _determine_focus_area(technologies: list[dict[str, Any]] | None) -> str | None:
    """Pick the dominant tech focus if one exists."""
    if not technologies:
        return None
    # Highest confidence tech
    sorted_techs = sorted(technologies, key=lambda t: t.get("confidence", 0), reverse=True)
    top = sorted_techs[0]["name"] if sorted_techs else None
    return top


def _generate_headline(
    person: dict[str, Any],
    events: list[dict[str, Any]],
    technologies: list[dict[str, Any]] | None,
    activity_type: str,
    top_repos: list[str],
) -> str:
    """Generate a punchy headline from the activity."""
    name = _name(person)
    tech_names = [t["name"] for t in (technologies or [])[:2] if t.get("name")]

    if activity_type == "release":
        return f"{name} shipped a release"
    if activity_type == "new_project":
        return f"{name} started a new project"
    if activity_type == "external_contribution":
        if tech_names:
            return f"{name} is contributing to {tech_names[0]} open source"
        return f"{name} made an external contribution"
    if activity_type == "deep_work":
        if len(top_repos) == 1:
            short = _repo_short(top_repos[0])
            if tech_names:
                return f"{name} is sustaining work on a {tech_names[0]} project"
            return f"{name} is sustaining work on {short}"
        if tech_names:
            return f"{name} is going deeper into {tech_names[0]}"
        if top_repos:
            short = top_repos[0].split("/")[-1] if "/" in top_repos[0] else top_repos[0]
            return f"{name} is focused on {short}"
        return f"{name} is actively building"
    if activity_type == "exploration":
        return f"{name} is exploring new territory"
    if tech_names:
        return f"{name} is working with {tech_names[0]}"
    if top_repos:
        short = top_repos[0].split("/")[-1] if "/" in top_repos[0] else top_repos[0]
        return f"{name} is active in {short}"
    return f"{name} was active this period"


def _short_repos(top_repos: list[str], limit: int = 3) -> list[str]:
    names = []
    for repo in top_repos[:limit]:
        names.append(repo.split("/")[-1] if "/" in repo else repo)
    return names


def _generate_summary(
    person: dict[str, Any],
    events: list[dict[str, Any]],
    activity_type: str,
    top_repos: list[str],
    tech_names: list[str],
) -> str:
    """Story-shaped summary. Avoid dumping raw event counters."""
    name = _name(person)
    repos = _short_repos(top_repos)
    repo_phrase = ""
    if len(repos) == 1:
        repo_phrase = f" in {repos[0]}"
    elif repos:
        repo_phrase = f" across {', '.join(repos)}"
    tech_phrase = f", with a focus on {tech_names[0]}" if tech_names else ""
    external = [e for e in events if _is_external(e, person)]

    if activity_type == "release":
        return f"{name} shipped a release{repo_phrase}{tech_phrase}."
    if activity_type == "new_project":
        return f"{name} started something new{repo_phrase}."
    if activity_type == "external_contribution":
        target = _repo(external[0]) if external else None
        if target:
            return f"{name} contributed to {target}{tech_phrase}."
        return f"{name} made an external open-source contribution{tech_phrase}."
    if activity_type == "deep_work":
        return f"{name} did focused work{repo_phrase}{tech_phrase}."
    if activity_type == "exploration":
        return f"{name} explored new repositories{repo_phrase}."
    if repos or tech_names:
        return f"{name} continued work{repo_phrase}{tech_phrase}."
    return f"{name} had public GitHub activity this period."


def _generate_why_it_matters(
    events: list[dict[str, Any]],
    person: dict[str, Any],
    activity_type: str,
    technologies: list[dict[str, Any]] | None,
) -> str | None:
    """Generate a grounded 'why it matters' tied to the dominant activity type."""
    external_prs = [
        e
        for e in events
        if _event_type(e) in ("pull_request_opened", "pull_request_merged")
        and _is_external(e, person)
    ]
    releases = [e for e in events if _event_type(e) == "release_published"]
    repos = {_repo(e) for e in events if _repo(e)}
    tech_names = [t["name"] for t in (technologies or [])[:3] if t.get("name")]

    if activity_type == "release":
        release_repos = {_repo(e) for e in releases if _repo(e)}
        if len(release_repos) >= 2:
            repos_short = ", ".join(_repo_short(r) for r in sorted(release_repos)[:2])
            return (
                f"Shipping releases across {repos_short} suggests active maintenance "
                "across multiple projects."
            )
        return "A release usually means a project is moving into delivery or active upkeep."

    if activity_type == "new_project":
        return "A new repository often signals exploration into a fresh idea or problem space."

    if activity_type == "external_contribution":
        if len(external_prs) >= 2:
            return (
                "Several external contributions suggest deepening participation "
                "in projects beyond their own repositories."
            )
        if external_prs:
            target = _repo(external_prs[0])
            if target:
                return (
                    f"Contributing to `{target}` places their recent activity inside "
                    "a project beyond their own repository."
                )
        if tech_names:
            return f"Contributing externally in {tech_names[0]} connects their work to a broader ecosystem."
        return "External contributions show involvement outside their own repositories."

    if activity_type == "deep_work":
        if len(repos) == 1:
            short = _repo_short(next(iter(repos)))
            return f"Repeated work in `{short}` suggests sustained investment in a specific problem."
        if tech_names:
            return f"Continued focus on {tech_names[0]} suggests deepening expertise in that area."
        return "Focused pull request and review activity suggests sustained engineering work."

    if activity_type == "exploration":
        return "Activity across new repositories can signal experimentation or surveying new tools."

    if len(repos) >= 4:
        return f"Work spread across {len(repos)} repositories suggests broad engagement this period."

    if tech_names:
        return f"Repeated {tech_names[0]} activity suggests a sustained focus this period."

    return None


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


def template_narrative_enriched(
    person: dict[str, Any],
    events: list[dict[str, Any]],
    technologies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return enriched narrative dict with headline, why_it_matters, etc."""
    if not events:
        narrative_text, event_ids, model = template_narrative(person, events, technologies)
        return {
            "headline": f"{_name(person)} was quiet",
            "narrative": narrative_text,
            "why_it_matters": None,
            "focus_area": None,
            "activity_type": "routine",
            "technologies_mentioned": [],
            "supporting_event_ids": event_ids,
            "model_used": model,
        }

    repos = [r for e in events if (r := _repo(e))]
    top_repos = [name for name, _ in Counter(repos).most_common(3)]
    activity_type = _determine_activity_type(events, person)
    focus_area = _determine_focus_area(technologies)
    headline = _generate_headline(person, events, technologies, activity_type, top_repos)
    why_it_matters = _generate_why_it_matters(events, person, activity_type, technologies)
    tech_names = [t["name"] for t in (technologies or [])[:4] if t.get("name")]
    summary = _generate_summary(person, events, activity_type, top_repos, tech_names)
    event_ids = [e["id"] for e in events if e.get("id") is not None]

    return {
        "headline": headline,
        "narrative": summary,
        "why_it_matters": why_it_matters,
        "focus_area": focus_area,
        "activity_type": activity_type,
        "technologies_mentioned": tech_names,
        "supporting_event_ids": event_ids[:20],
        "model_used": "template",
    }


def activity_digest(events: list[dict[str, Any]]) -> dict[str, Any]:
    repos = [r for e in events if (r := _repo(e))]
    return {
        "event_count": len(events),
        "significance_total": sum(int(e.get("significance_score") or 0) for e in events),
        "top_repos": [name for name, _ in Counter(repos).most_common(3)],
        "counts": dict(Counter(_event_type(e) for e in events if _event_type(e))),
    }
