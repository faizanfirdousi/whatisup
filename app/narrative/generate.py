import json
import logging
from typing import Any
import httpx

from app.config import get_settings
from app.narrative.schema import WeeklyNarrative
from app.narrative.prompts import SYSTEM_PROMPT
from app.narrative.template import template_narrative, template_narrative_enriched

logger = logging.getLogger(__name__)


def passes_grounding_check(
    output: WeeklyNarrative,
    allowed_technologies: set[str],
    allowed_event_ids: set[int]
) -> bool:
    """Validate that the LLM only cited allowed facts."""
    for tech in output.technologies_mentioned:
        if tech.lower() not in allowed_technologies:
            logger.warning("Validation failed: Hallucinated technology '%s'", tech)
            return False

    for event_id in output.supporting_event_ids:
        if event_id not in allowed_event_ids:
            logger.warning("Validation failed: Hallucinated event ID '%s'", event_id)
            return False

    return True


def sanitize_narrative(
    output: WeeklyNarrative,
    allowed_technologies: set[str],
    allowed_event_ids: set[int],
) -> WeeklyNarrative | None:
    """Drop hallucinated citations instead of discarding a usable paragraph."""
    techs = [t for t in output.technologies_mentioned if t.lower() in allowed_technologies]
    event_ids = [i for i in output.supporting_event_ids if i in allowed_event_ids]
    if not output.narrative.strip():
        return None
    return WeeklyNarrative(
        headline=output.headline,
        narrative=output.narrative,
        why_it_matters=output.why_it_matters,
        technologies_mentioned=techs,
        supporting_event_ids=event_ids,
        focus_area=output.focus_area,
        activity_type=output.activity_type,
    )


def _narrative_to_enriched(parsed: WeeklyNarrative, model_name: str) -> dict[str, Any]:
    """Convert a parsed WeeklyNarrative to the enriched dict format."""
    return {
        "headline": parsed.headline,
        "narrative": parsed.narrative,
        "why_it_matters": parsed.why_it_matters,
        "focus_area": parsed.focus_area,
        "activity_type": parsed.activity_type,
        "technologies_mentioned": parsed.technologies_mentioned,
        "supporting_event_ids": parsed.supporting_event_ids,
        "model_used": model_name,
    }


async def generate_weekly_narrative(
    person: dict[str, Any],
    events: list[dict[str, Any]],
    technologies: list[dict[str, Any]],
) -> tuple[str, list[int], str]:
    """
    Call OpenRouter LLM to generate narrative.
    Returns (narrative_text, supporting_event_ids, model_used).
    """
    settings = get_settings()
    template_text, template_ids, template_model = template_narrative(person, events, technologies)

    if not events:
        return template_text, template_ids, template_model

    if not settings.openrouter_api_key:
        return template_text, template_ids, template_model
        
    allowed_technologies = {t["name"].lower() for t in technologies}
    allowed_event_ids = {e["id"] for e in events}
    
    # Prepare context
    context = {
        "person": {
            "username": person["github_username"],
            "display_name": person.get("display_name")
        },
        "technologies": technologies,
        "events": [
            {
                "id": e["id"],
                "type": e["event_type"],
                "repo": e["repo_full_name"],
                "date": e["occurred_at"].isoformat() if hasattr(e["occurred_at"], "isoformat") else str(e["occurred_at"]),
                "score": e["significance_score"],
                "metadata": e.get("metadata_", {})
            }
            for e in events
        ]
    }
    
    # JSON schema for OpenRouter / OpenAI
    schema = WeeklyNarrative.model_json_schema()

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": settings.public_app_url,
        "X-Title": "WhatIsUp",
    }
    
    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context)}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "WeeklyNarrative",
                "schema": schema,
                "strict": True
            }
        },
        "temperature": 0.0
    }
    
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code >= 400:
                # Many free models reject json_schema; retry as plain JSON.
                logger.warning("Structured output rejected (%s); retrying without schema", resp.status_code)
                payload.pop("response_format", None)
                payload["messages"][0]["content"] = (
                    SYSTEM_PROMPT + "\nRespond with JSON only: "
                    '{"headline": str, "narrative": str, "why_it_matters": str|null, '
                    '"technologies_mentioned": [str], "supporting_event_ids": [int], '
                    '"focus_area": str|null, "activity_type": str|null}'
                )
                resp = await client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()

            raw_content = data["choices"][0]["message"]["content"] or ""
            text = raw_content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                if text.endswith("```"):
                    text = text[: text.rfind("```")]
            parsed = WeeklyNarrative.model_validate_json(text.strip())
            cleaned = sanitize_narrative(parsed, allowed_technologies, allowed_event_ids)
            if cleaned:
                return cleaned.narrative, cleaned.supporting_event_ids or template_ids, data.get("model", settings.openrouter_model)
            if passes_grounding_check(parsed, allowed_technologies, allowed_event_ids):
                return parsed.narrative, parsed.supporting_event_ids, data.get("model", settings.openrouter_model)
            logger.warning("LLM narrative failed grounding; using template")
            return template_text, template_ids, template_model

    except Exception as e:
        logger.error("Error generating narrative: %s", e)
        return template_text, template_ids, template_model


async def generate_weekly_narrative_enriched(
    person: dict[str, Any],
    events: list[dict[str, Any]],
    technologies: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Generate an enriched narrative with headline, why_it_matters, etc.
    Returns a dict with all enriched fields.
    """
    settings = get_settings()
    enriched_template = template_narrative_enriched(person, events, technologies)

    if not events or not settings.openrouter_api_key:
        return enriched_template

    allowed_technologies = {t["name"].lower() for t in technologies}
    allowed_event_ids = {e["id"] for e in events}

    context = {
        "person": {
            "username": person["github_username"],
            "display_name": person.get("display_name"),
        },
        "technologies": technologies,
        "events": [
            {
                "id": e["id"],
                "type": e["event_type"],
                "repo": e["repo_full_name"],
                "date": (
                    e["occurred_at"].isoformat()
                    if hasattr(e["occurred_at"], "isoformat")
                    else str(e["occurred_at"])
                ),
                "score": e["significance_score"],
                "metadata": e.get("metadata_", {}),
            }
            for e in events
        ],
    }

    schema = WeeklyNarrative.model_json_schema()
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": settings.public_app_url,
        "X-Title": "WhatIsUp",
    }
    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "WeeklyNarrative", "schema": schema, "strict": True},
        },
        "temperature": 0.0,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code >= 400:
                payload.pop("response_format", None)
                payload["messages"][0]["content"] = (
                    SYSTEM_PROMPT + "\nRespond with JSON only."
                )
                resp = await client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"] or ""
            text = raw_content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                if text.endswith("```"):
                    text = text[: text.rfind("```")]
            parsed = WeeklyNarrative.model_validate_json(text.strip())
            cleaned = sanitize_narrative(parsed, allowed_technologies, allowed_event_ids)
            result = cleaned or parsed
            if cleaned or passes_grounding_check(parsed, allowed_technologies, allowed_event_ids):
                return _narrative_to_enriched(result, data.get("model", settings.openrouter_model))
            logger.warning("Enriched LLM narrative failed grounding; using template")
    except Exception as e:
        logger.error("Error generating enriched narrative: %s", e)

    return enriched_template
