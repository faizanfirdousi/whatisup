"""Network-level intelligence derived from facts — hero thesis, movement, clusters."""

from __future__ import annotations

from typing import Any

from app.scoring.canonical import canonical_key, display_name

CLUSTER_THEMES: dict[str, set[str]] = {
    "cloud-native infrastructure": {
        "kubernetes", "helm", "docker", "opentelemetry", "go", "prometheus", "terraform",
    },
    "developer tooling": {
        "typescript", "node.js", "javascript", "python", "automation", "cli", "devtools",
    },
    "ai systems": {
        "ai-agents", "inference", "machine-learning",
    },
}

MAX_HERO_SIGNALS = 3
MAX_NETWORK_STORIES = 3
MAX_SIMILAR_PEOPLE = 3


def _cap(name: str) -> str:
    return display_name(name) if name else name


def _matches_theme(tech_name: str, keywords: set[str]) -> bool:
    key = canonical_key(tech_name)
    return key in keywords or any(keyword in key or key in keyword for keyword in keywords)


def _tech_row(facts: dict, name: str) -> dict | None:
    key = canonical_key(name)
    for row in facts.get("tech_this_week") or []:
        if canonical_key(row["name"]) == key:
            return row
    return None


def _likely_tracking_artifact(tech_row: dict[str, Any]) -> bool:
    people = len(tech_row.get("person_ids") or [])
    new_people = len(tech_row.get("new_to_person_ids") or [])
    if people == 0:
        return True
    return new_people >= max(2, round(people * 0.6))


def _rising_with_history(facts: dict, tech_name: str) -> bool:
    for row in facts.get("rising") or []:
        if canonical_key(row["name"]) != canonical_key(tech_name):
            continue
        prior = float(row.get("prior_4w_avg_people") or 0)
        return prior >= 1.0
    return False


def _tech_evidence_item(facts: dict, tech_row: dict[str, Any]) -> dict[str, Any]:
    label = _cap(tech_row["name"])
    people = len(tech_row.get("person_ids") or [])
    key = canonical_key(tech_row["name"])
    if _rising_with_history(facts, tech_row["name"]) and not _likely_tracking_artifact(tech_row):
        body = (
            f"{label} activity increased vs the prior period "
            f"({people} people active recently)."
        )
    else:
        body = f"{people} people had recent activity involving {label}."
    return {"id": f"tech:{key}", "title": label, "body": body, "tech": key}


def direction_area_for_techs(tech_names: list[str]) -> str | None:
    keys = {canonical_key(t) for t in tech_names if t}
    themes = _themes_for_techs(keys)
    if not themes:
        return None
    return next(iter(sorted(themes))).title()


def _themes_for_techs(tech_keys: set[str]) -> set[str]:
    themes: set[str] = set()
    for theme, keywords in CLUSTER_THEMES.items():
        if tech_keys & keywords or any(_matches_theme(t, keywords) for t in tech_keys):
            themes.add(theme)
    return themes


def technology_movement(facts: dict) -> dict[str, list[dict[str, Any]]]:
    rising_by_name = {row["name"]: row for row in facts.get("rising") or []}
    new_by_name = {row["name"]: row for row in facts.get("new_in_network") or []}

    established: list[dict[str, Any]] = []
    growing: list[dict[str, Any]] = []
    new_techs: list[dict[str, Any]] = []

    for row in facts.get("tech_this_week") or []:
        name = row["name"]
        people_count = len(row.get("person_ids") or [])
        if people_count == 0:
            continue

        if name in new_by_name:
            new_techs.append(
                {
                    "name": name,
                    "people_count": len(new_by_name[name].get("person_ids") or []),
                    "signal": "New across your network this period",
                }
            )
            continue

        if name in rising_by_name:
            rising = rising_by_name[name]
            prior = float(rising.get("prior_4w_avg_people") or 0)
            delta = max(0, people_count - round(prior))
            growing.append(
                {
                    "name": name,
                    "people_count": people_count,
                    "prior_avg_people": round(prior, 1),
                    "delta_people": delta,
                    "signal": (
                        f"{people_count} people active recently, up from ~{prior:.1f} on average"
                        if prior > 0
                        else f"{people_count} people active recently"
                    ),
                }
            )
            continue

        if people_count >= 2:
            established.append({"name": name, "people_count": people_count})

    established.sort(key=lambda item: item["people_count"], reverse=True)
    growing.sort(key=lambda item: item.get("delta_people", 0), reverse=True)
    new_techs.sort(key=lambda item: item["people_count"], reverse=True)

    return {
        "established": established[:5],
        "growing": growing[:5],
        "new": new_techs[:5],
    }


def network_clusters(facts: dict) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    tech_rows = facts.get("tech_this_week") or []

    for theme, keywords in CLUSTER_THEMES.items():
        matching_techs: set[str] = set()
        people: set[int] = set()
        for row in tech_rows:
            if _matches_theme(row["name"], keywords):
                matching_techs.add(row["name"])
                people.update(row.get("person_ids") or [])
        if len(people) < 2:
            continue
        clusters.append(
            {
                "id": theme.replace(" ", "-"),
                "headline": theme.title(),
                "summary": (
                    f"{len(people)} people recently worked with related technologies "
                    f"in this area."
                ),
                "technologies": sorted({display_name(t) for t in matching_techs})[:6],
                "people_count": len(people),
                "repos": [],
            }
        )

    for repo_row in (facts.get("shared_repos") or [])[:2]:
        repo = repo_row["repo"]
        short = repo.split("/")[-1] if "/" in repo else repo
        clusters.append(
            {
                "id": f"repo:{repo}",
                "headline": short,
                "summary": (
                    f"{repo_row['people_count']} people in your network "
                    f"interacted with {repo}."
                ),
                "technologies": [],
                "people_count": repo_row["people_count"],
                "repos": [repo],
            }
        )

    clusters.sort(key=lambda item: item["people_count"], reverse=True)
    return clusters[:3]


def network_signals(
    facts: dict,
    movement: dict[str, list[dict[str, Any]]],
    clusters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deprecated — hero uses a single cta link instead of signal chips."""
    del facts, movement, clusters
    return []


def build_hero(
    facts: dict,
    movement: dict[str, list[dict[str, Any]]],
    clusters: list[dict[str, Any]],
    curated_stories: list[dict[str, Any]],
) -> dict[str, Any]:
    """Hero states the network conclusion; technology evidence lives in story cards."""
    del curated_stories
    theme_clusters = [c for c in clusters if not c.get("repos")]
    top_cluster = theme_clusters[0] if theme_clusters else None

    if top_cluster:
        headline = f"{top_cluster['headline']} is the strongest active theme in your network"
        techs = top_cluster.get("technologies") or []
        count = top_cluster["people_count"]
        if len(techs) >= 2:
            tech_phrase = ", ".join(_cap(t) for t in techs[:4])
            subhead = (
                f"{count} people recently worked across {tech_phrase}, and related technologies."
            )
        else:
            subhead = top_cluster["summary"].rstrip(".") + "."
        cta = {
            "label": f"Explore {top_cluster['headline']}",
            "href": "/network",
        }
    else:
        active = len(facts.get("active_person_ids") or [])
        headline = "What's active in your network"
        subhead = (
            f"{active} people had tracked public activity this period."
            if active
            else "We'll highlight meaningful shifts as patterns emerge across your network."
        )
        cta = {"label": "Explore network", "href": "/network"}

    return {
        "headline": headline,
        "subhead": subhead,
        "cta": cta,
        "signals": network_signals(facts, movement, clusters),
    }


def shared_activity(facts: dict, movement: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Honest network-level activity items with temporal context where available."""
    items: list[dict[str, Any]] = []

    for row in movement.get("growing") or []:
        items.append(
            {
                "type": "growing_tech",
                "headline": f"{_cap(row['name'])} is increasing",
                "detail": row["signal"],
                "people_count": row["people_count"],
                "technologies": [row["name"]],
            }
        )

    for row in movement.get("new") or []:
        items.append(
            {
                "type": "new_tech",
                "headline": f"{_cap(row['name'])} is new in your network",
                "detail": row["signal"],
                "people_count": row["people_count"],
                "technologies": [row["name"]],
            }
        )

    for row in facts.get("shared_repos") or []:
        items.append(
            {
                "type": "shared_repo",
                "headline": f"{row['people_count']} people interacted with {row['repo']}",
                "detail": "Multiple people in your network touched the same repository.",
                "people_count": row["people_count"],
                "repo": row["repo"],
            }
        )

    # Established techs that are widespread but not "emerging"
    for row in movement.get("established") or []:
        if row["people_count"] >= 3:
            items.append(
                {
                    "type": "established_tech",
                    "headline": f"{_cap(row['name'])} is active across your network",
                    "detail": f"{row['people_count']} people worked with it this period.",
                    "people_count": row["people_count"],
                    "technologies": [row["name"]],
                }
            )

    return items[:6]


def curated_network_stories(
    facts: dict,
    clusters: list[dict[str, Any]],
    movement: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Top technology evidence — honest observation copy, not trend claims."""
    del clusters, movement
    rows = sorted(
        facts.get("tech_this_week") or [],
        key=lambda r: len(r.get("person_ids") or []),
        reverse=True,
    )
    picked: list[dict[str, Any]] = []
    for row in rows:
        if len(row.get("person_ids") or []) < 2:
            continue
        picked.append(_tech_evidence_item(facts, row))
        if len(picked) >= MAX_NETWORK_STORIES:
            break
    return picked


def curate_for_you(
    facts: dict,
    usernames: dict[int, str],
    *,
    owner_techs: set[str] | None = None,
    clusters: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Network-relative insights — similar people and one relevant cluster."""
    owner_keys = {canonical_key(t) for t in (owner_techs or set())}
    owner_id = facts.get("owner_person_id")
    if not owner_keys:
        return None

    owner_themes = _themes_for_techs(owner_keys)

    person_data: dict[int, dict[str, Any]] = {}
    for row in facts.get("tech_this_week") or []:
        key = canonical_key(row["name"])
        owner_overlap = key in owner_keys or bool(_themes_for_techs({key}) & owner_themes)
        if not owner_overlap:
            continue
        themes = _themes_for_techs({key})
        for pid in row.get("person_ids") or []:
            if owner_id and pid == owner_id:
                continue
            login = usernames.get(pid)
            if not login:
                continue
            slot = person_data.setdefault(
                pid,
                {
                    "person_id": pid,
                    "github_username": login,
                    "technologies": set(),
                    "themes": set(),
                    "score": 0,
                },
            )
            slot["technologies"].add(_cap(row["name"]))
            slot["themes"].update(themes)
            if pid in (row.get("new_to_person_ids") or []):
                slot["score"] += 3
            slot["score"] += 1

    similar_people: list[dict[str, Any]] = []
    for pid, data in sorted(person_data.items(), key=lambda item: item[1]["score"], reverse=True):
        if len(similar_people) >= MAX_SIMILAR_PEOPLE:
            break
        theme = next(iter(sorted(data["themes"])), None)
        techs = sorted(data["technologies"])[:4]
        similar_people.append(
            {
                "person_id": pid,
                "github_username": data["github_username"],
                "technologies": techs,
                "cluster": theme.title() if theme else None,
                "hook": (
                    f"Also working with {' · '.join(techs[:3])}"
                    if techs
                    else "Moving in a related direction"
                ),
            }
        )

    relevant_cluster = None
    theme_clusters = [c for c in (clusters or []) if not c.get("repos")]
    best = None
    best_score = 0
    for cluster in theme_clusters:
        cluster_keys = {canonical_key(t) for t in cluster.get("technologies") or []}
        overlap = cluster_keys & owner_keys
        theme_match = cluster["id"].replace("-", " ") in owner_themes
        score = len(overlap) * 2 + (10 if theme_match else 0) + cluster.get("people_count", 0)
        if score > best_score:
            best_score = score
            best = cluster

    if best and best_score > 0:
        relevant_cluster = {
            "headline": best["headline"],
            "summary": (
                f"{best['people_count']} people in your network are active around "
                f"{', '.join(_cap(t) for t in (best.get('technologies') or [])[:4])}."
            ),
            "technologies": [_cap(t) for t in (best.get("technologies") or [])[:6]],
            "people_count": best["people_count"],
            "explore_tech": (best.get("technologies") or [None])[0],
            "cluster_id": best["id"],
        }

    if not similar_people and not relevant_cluster:
        return None

    return {
        "similar_people": similar_people,
        "relevant_cluster": relevant_cluster,
    }


def owner_network_alignment(facts: dict, owner_techs: set[str]) -> str | None:
    """One-line alignment between owner tech and rising network trends."""
    owner_keys = {canonical_key(t) for t in owner_techs}
    owner_themes = _themes_for_techs(owner_keys)
    labels: list[str] = []
    seen: set[str] = set()
    for row in facts.get("rising") or []:
        key = canonical_key(row["name"])
        if key in owner_keys or bool(_themes_for_techs({key}) & owner_themes):
            label = display_name(row["name"])
            if label.lower() not in seen:
                seen.add(label.lower())
                labels.append(label)
    if not labels:
        return None
    verb = "is" if len(labels) == 1 else "are"
    return f"{', '.join(labels[:3])} {verb} rising across your network too"


def network_story(
    facts: dict,
    clusters: list[dict[str, Any]],
    movement: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Curated network stories only — no duplicate chips or metrics."""
    stories = curated_network_stories(facts, clusters, movement)
    return {"stories": stories}


def build_network_intelligence(
    facts: dict,
    *,
    usernames: dict[int, str] | None = None,
    owner_techs: set[str] | None = None,
    owner_focus: str | None = None,
    close_people: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    del owner_focus, close_people  # reserved for future quiet-circle curation
    movement = technology_movement(facts)
    clusters = network_clusters(facts)
    curated_stories = curated_network_stories(facts, clusters, movement)
    hero = build_hero(facts, movement, clusters, curated_stories)
    story = network_story(facts, clusters, movement)
    for_you = curate_for_you(
        facts,
        usernames or {},
        owner_techs=owner_techs,
        clusters=clusters,
    )
    return {
        "hero": hero,
        "story": story,
        "for_you": for_you,
        # Available for /network explore — not rendered on homepage
        "technology_movement": movement,
        "clusters": clusters,
        "shared_activity": shared_activity(facts, movement),
    }


def infer_focus(
    focus_area: str | None,
    technologies: list[str],
    active_repos: list[str],
) -> str | None:
    if focus_area:
        return focus_area
    if technologies and active_repos:
        repo = active_repos[0].split("/")[-1] if "/" in active_repos[0] else active_repos[0]
        return f"{technologies[0]} work in {repo}"
    if technologies:
        return f"{technologies[0]} projects"
    if len(active_repos) == 1:
        return active_repos[0].split("/")[-1] if "/" in active_repos[0] else active_repos[0]
    if len(active_repos) > 1:
        first = active_repos[0].split("/")[-1] if "/" in active_repos[0] else active_repos[0]
        return f"{first} and {len(active_repos) - 1} other repos"
    return None
