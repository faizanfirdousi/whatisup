import json
import logging
import re
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.network_story import NetworkStory
from app.models.person import Person
from app.network.facts import all_person_ids_from_facts, all_tech_names_from_facts, compute_network_facts
from app.pipeline import current_week_bounds

logger = logging.getLogger(__name__)

NETWORK_STORY_PROMPT = """You write a short weekly briefing about a developer's GitHub network.

You receive structured facts only: counts, person ids, technology names.
Do not invent counts, names, or technologies.
Do not infer motives, career pivots, boredom, or plans.
Do not mention anyone whose id is not in the facts.
Write 3-6 bullets. Optional interesting sentence only if rising or new_in_network is present.
Return JSON only.
"""


class NetworkStoryOut(BaseModel):
    headline: str
    bullets: list[str]
    interesting: str | None = None
    cited_person_ids: list[int] = Field(default_factory=list)
    cited_techs: list[str] = Field(default_factory=list)
    network_pulse: dict = Field(default_factory=dict)
    top_technologies: list[dict] = Field(default_factory=list)
    shared_repos: list[dict] = Field(default_factory=list)


def template_network_story(facts: dict, usernames: dict[int, str]) -> NetworkStoryOut:
    bullets: list[str] = []
    cited_people: set[int] = set()
    cited_techs: set[str] = set()

    for row in facts.get("tech_this_week") or []:
        n = len(row.get("person_ids") or [])
        if n >= 2:
            bullets.append(f"{n} people worked with {row['name']}-related projects")
            cited_techs.add(row["name"])
            cited_people.update(row["person_ids"])

    firsts = facts.get("first_external_oss") or []
    if firsts:
        bullets.append(
            f"{len(firsts)} people started contributing to open source (first external PR in tracked history)"
        )
        cited_people.update(f["person_id"] for f in firsts)

    for row in facts.get("rising") or []:
        bullets.append(
            f"{row['name']} activity increased vs the prior 4 weeks "
            f"({row['this_week_people']} people this week, 4-week average {row['prior_4w_avg_people']})"
        )
        cited_techs.add(row["name"])

    for row in facts.get("new_in_network") or []:
        names = ", ".join(f"`{row['name']}`" for _ in [row])
        bullets.append(
            f"People independently showed {names} who had not had those techs before"
        )
        cited_techs.add(row["name"])
        cited_people.update(row.get("person_ids") or [])

    quiet = facts.get("quiet_close_person_ids") or []
    close_size = facts.get("close_circle_size") or 0
    if quiet and close_size:
        bullets.append(
            f"Close circle was quiet: {len(quiet)} of {close_size} close connections had no events this week"
        )
        cited_people.update(quiet)

    if not bullets:
        bullets.append("No broader network pattern is visible yet.")

    interesting = None
    rising = facts.get("rising") or []
    new_in = facts.get("new_in_network") or []
    if rising:
        top = rising[0]
        extra = ""
        for row in facts.get("tech_this_week") or []:
            if row["name"] == top["name"] and row.get("new_to_person_ids"):
                extra = (
                    f" {len(row['new_to_person_ids'])} of those people had never used it "
                    "in tracked repositories before."
                )
                break
        interesting = (
            f"{top['name']} appeared in repositories belonging to {top['this_week_people']} "
            f"people you follow this week.{extra}"
        )
    elif new_in:
        row = new_in[0]
        interesting = (
            f"{row['name']} is new in your network this week "
            f"({len(row.get('person_ids') or [])} people)."
        )

    active = len(facts.get("active_person_ids") or [])
    headline = f"{active} people in your network were active this week"
    
    pulse = facts.get("people_by_activity_level") or {}
    network_pulse = {
        "more_active": len(pulse.get("more_active", [])),
        "steady": len(pulse.get("steady", [])),
        "quiet": len(pulse.get("quiet", [])),
    }
    
    top_techs = []
    for row in facts.get("tech_this_week") or []:
        top_techs.append({
            "name": row["name"],
            "people_count": len(row.get("person_ids") or []),
            "direction": "steady" # default
        })
    for row in facts.get("rising") or []:
        for t in top_techs:
            if t["name"] == row["name"]:
                t["direction"] = "up"
    for row in facts.get("declining") or []:
        top_techs.append({
            "name": row["name"],
            "people_count": 0,
            "direction": "down"
        })
    top_techs.sort(key=lambda x: x["people_count"], reverse=True)
    
    shared_repos = facts.get("shared_repos") or []
    
    return NetworkStoryOut(
        headline=headline,
        bullets=bullets[:6],
        interesting=interesting,
        cited_person_ids=sorted(cited_people),
        cited_techs=sorted(cited_techs),
        network_pulse=network_pulse,
        top_technologies=top_techs[:5],
        shared_repos=shared_repos[:5],
    )


def validate_network_story(
    out: NetworkStoryOut, facts: dict, usernames: dict[int, str]
) -> bool:
    if not (1 <= len(out.bullets) <= 6):
        return False
    allowed_people = all_person_ids_from_facts(facts)
    allowed_techs = all_tech_names_from_facts(facts)
    for pid in out.cited_person_ids:
        if pid not in allowed_people:
            logger.warning("Network story cited unknown person_id %s", pid)
            return False
    for tech in out.cited_techs:
        if tech.lower() not in allowed_techs:
            logger.warning("Network story cited unknown tech %s", tech)
            return False
    known_logins = {u.lower() for u in usernames.values()}
    blob = " ".join([out.headline, *(out.bullets), out.interesting or ""])
    for match in re.findall(r"@([A-Za-z0-9-]+)", blob):
        if match.lower() not in known_logins:
            logger.warning("Network story mentioned unknown @%s", match)
            return False
    return True


def _story_to_text(out: NetworkStoryOut) -> str:
    parts = [out.headline]
    parts.extend(f"- {b}" for b in out.bullets)
    if out.interesting:
        parts.append(out.interesting)
    return "\n".join(parts)


async def _llm_network_story(facts: dict, usernames: dict[int, str]) -> NetworkStoryOut | None:
    settings = get_settings()
    if not settings.openrouter_api_key:
        return None
    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": NETWORK_STORY_PROMPT},
            {
                "role": "user",
                "content": json.dumps({"facts": facts, "usernames": usernames}),
            },
        ],
        "temperature": 0.0,
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": settings.public_app_url,
                    "X-Title": "WhatIsUp",
                },
                json=payload,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"] or ""
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                if text.endswith("```"):
                    text = text[: text.rfind("```")]
            parsed = NetworkStoryOut.model_validate_json(text.strip())
            if validate_network_story(parsed, facts, usernames):
                return parsed
            logger.warning("Network story failed grounding; using template")
    except Exception as e:
        logger.error("Network story LLM error: %s", e)
    return None


async def generate_network_story(
    session: AsyncSession, owner_id: int, facts: dict | None = None
) -> NetworkStory:
    facts = facts or await compute_network_facts(session, owner_id)
    week_start, week_end, _, _ = current_week_bounds()
    ids = list(all_person_ids_from_facts(facts))
    usernames: dict[int, str] = {}
    if ids:
        res = await session.execute(select(Person.id, Person.github_username).where(Person.id.in_(ids)))
        usernames = {row.id: row.github_username for row in res.all()}

    templated = template_network_story(facts, usernames)
    llm = await _llm_network_story(facts, usernames)
    out = llm or templated
    
    if llm:
        out.network_pulse = templated.network_pulse
        out.top_technologies = templated.top_technologies
        out.shared_repos = templated.shared_repos

    model = get_settings().openrouter_model if llm else "template"

    res = await session.execute(
        select(NetworkStory).where(
            NetworkStory.owner_id == owner_id, NetworkStory.week_start == week_start
        )
    )
    row = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    text = json.dumps(out.model_dump())
    if row:
        row.facts = facts
        row.narrative_text = text
        row.model_used = model
        row.generated_at = now
        row.week_end = week_end
    else:
        row = NetworkStory(
            owner_id=owner_id,
            week_start=week_start,
            week_end=week_end,
            facts=facts,
            narrative_text=text,
            model_used=model,
        )
        session.add(row)
    await session.flush()
    return row
