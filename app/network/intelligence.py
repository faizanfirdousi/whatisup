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
    """At most three hero signals — summary only, detail lives below."""
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in movement.get("growing") or []:
        key = canonical_key(row["name"])
        if key in seen:
            continue
        seen.add(key)
        signals.append(
            {
                "name": key,
                "direction": "up",
                "label": f"{_cap(row['name'])} ↑",
                "description": row["signal"],
            }
        )
        break

    external = facts.get("first_external_oss") or []
    if len(external) >= 2:
        signals.append(
            {
                "name": "open-source",
                "direction": "up",
                "label": "Open source ↑",
                "description": f"{len(external)} first tracked external contributions",
            }
        )

    for cluster in clusters:
        if cluster.get("repos"):
            continue
        theme_id = cluster.get("id", "")
        if theme_id in seen:
            continue
        seen.add(theme_id)
        signals.append(
            {
                "name": theme_id,
                "direction": "cluster",
                "label": cluster["headline"],
                "description": cluster["summary"],
            }
        )
        break

    if len(signals) < MAX_HERO_SIGNALS:
        for row in movement.get("new") or []:
            key = canonical_key(row["name"])
            if key in seen:
                continue
            seen.add(key)
            signals.append(
                {
                    "name": key,
                    "direction": "new",
                    "label": f"{_cap(row['name'])} new",
                    "description": row["signal"],
                }
            )
            if len(signals) >= MAX_HERO_SIGNALS:
                break

    return signals[:MAX_HERO_SIGNALS]


def build_hero(
    facts: dict,
    movement: dict[str, list[dict[str, Any]]],
    clusters: list[dict[str, Any]],
    curated_stories: list[dict[str, Any]],
) -> dict[str, Any]:
    external = facts.get("first_external_oss") or []
    growing = movement.get("growing") or []
    top_cluster = next((c for c in clusters if not c.get("repos")), None)

    headline_parts: list[str] = []
    if external and len(external) >= 2:
        headline_parts.append("open source")
    if growing:
        headline_parts.append(_cap(growing[0]["name"]))
    elif top_cluster:
        headline_parts.append(top_cluster["headline"].lower())

    if len(headline_parts) >= 2:
        headline = f"Your network is shifting toward {headline_parts[0]} and {headline_parts[1]}"
    elif headline_parts:
        headline = f"Your network is shifting toward {headline_parts[0]}"
    elif curated_stories:
        headline = curated_stories[0]["title"]
    else:
        headline = "What's changing in your network"

    subhead_parts: list[str] = []
    if external and len(external) >= 2:
        subhead_parts.append(
            f"{len(external)} people made first tracked external contributions"
        )
    if growing:
        row = _tech_row(facts, growing[0]["name"])
        new_count = len(row.get("new_to_person_ids") or []) if row else 0
        label = _cap(growing[0]["name"])
        if new_count:
            subhead_parts.append(
                f"{label} appeared in newly tracked contexts for {new_count} people"
            )
        else:
            subhead_parts.append(f"{label} is appearing more often across your network")
    elif top_cluster:
        subhead_parts.append(top_cluster["summary"].rstrip("."))

    subhead = (
        ". ".join(subhead_parts) + "."
        if subhead_parts
        else "We'll highlight meaningful shifts as patterns emerge across your network."
    )

    return {
        "headline": headline,
        "subhead": subhead,
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
    """2–3 specific network stories — not activity metrics."""
    candidates: list[dict[str, Any]] = []
    used_themes: set[str] = set()

    rising = facts.get("rising") or []
    new_in = facts.get("new_in_network") or []
    spread_sources = rising or new_in or movement.get("new") or []

    for row in spread_sources:
        key = canonical_key(row.get("name", ""))
        if key in used_themes:
            continue
        tech_row = _tech_row(facts, row["name"])
        if not tech_row:
            continue
        people = len(tech_row.get("person_ids") or [])
        new_people = len(tech_row.get("new_to_person_ids") or [])
        if people < 2:
            continue
        label = _cap(row["name"])
        if new_people >= 2:
            body = (
                f"{people} people worked with {label} this period, "
                f"and it was newly tracked for {new_people} of them."
            )
            priority = 100 + new_people
        else:
            body = f"{people} people worked with {label} in newly active parts of your network."
            priority = 60 + people
        candidates.append(
            {
                "id": f"spread:{key}",
                "title": f"{label} is spreading through your network",
                "body": body,
                "tech": key,
                "priority": priority,
            }
        )
        used_themes.add(key)

    external = facts.get("first_external_oss") or []
    if len(external) >= 2:
        candidates.append(
            {
                "id": "oss:participation",
                "title": "Open-source participation is increasing",
                "body": (
                    f"{len(external)} people made their first tracked external "
                    "contribution during this period."
                ),
                "priority": 90 + len(external),
            }
        )

    theme_clusters = [c for c in clusters if not c.get("repos")]
    if theme_clusters:
        top = theme_clusters[0]
        tech_labels = ", ".join(_cap(t) for t in (top.get("technologies") or [])[:4])
        candidates.append(
            {
                "id": f"cluster:{top['id']}",
                "title": f"{top['headline']} is the strongest cluster",
                "body": (
                    f"{tech_labels} connect activity across "
                    f"{top['people_count']} people in your network."
                    if tech_labels
                    else top["summary"]
                ),
                "priority": 70 + top["people_count"],
            }
        )

    candidates.sort(key=lambda item: item["priority"], reverse=True)
    picked: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for story in candidates:
        if story["id"] in seen_ids:
            continue
        seen_ids.add(story["id"])
        picked.append({k: v for k, v in story.items() if k != "priority"})
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
    """Three curated personal insights — direction, similar people, one cluster."""
    owner_keys = {canonical_key(t) for t in (owner_techs or set())}
    if not owner_keys:
        return None

    owner_themes = _themes_for_techs(owner_keys)
    direction = None
    related_labels: list[str] = []
    for row in facts.get("rising") or []:
        key = canonical_key(row["name"])
        if key in owner_keys or _themes_for_techs({key}) & owner_themes:
            related_labels.append(_cap(row["name"]))
    for row in facts.get("tech_this_week") or []:
        key = canonical_key(row["name"])
        if key in owner_keys and len(row.get("person_ids") or []) >= 2:
            related_labels.append(_cap(row["name"]))

    unique_labels = []
    seen: set[str] = set()
    for label in related_labels:
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_labels.append(label)

    if unique_labels:
        direction = {
            "headline": "Your recent work aligns with a growing part of your network",
            "summary": (
                f"{', '.join(unique_labels[:3])} "
                f"{'is' if len(unique_labels) == 1 else 'are'} appearing more frequently "
                "among people you follow."
            ),
        }

    # Merge per-person convergence at cluster level
    person_data: dict[int, dict[str, Any]] = {}
    for row in facts.get("tech_this_week") or []:
        key = canonical_key(row["name"])
        owner_overlap = key in owner_keys or bool(_themes_for_techs({key}) & owner_themes)
        if not owner_overlap:
            continue
        themes = _themes_for_techs({key})
        for pid in row.get("person_ids") or []:
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
        similar_people.append(
            {
                "person_id": pid,
                "github_username": data["github_username"],
                "technologies": sorted(data["technologies"])[:4],
                "cluster": theme.title() if theme else None,
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

    if not direction and not similar_people and not relevant_cluster:
        return None

    return {
        "direction": direction,
        "similar_people": similar_people,
        "relevant_cluster": relevant_cluster,
    }


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
