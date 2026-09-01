"""Separate interestingness from raw significance — relevance to the viewer matters."""

from __future__ import annotations

from typing import Any

from app.scoring.canonical import canonical_key


def compute_interestingness(
    *,
    activity_type: str,
    meaningful_changes: int,
    technologies: list[str],
    is_close: bool,
    owner_techs: set[str],
    network_rising: set[str],
    trend_direction: str | None,
    has_why: bool,
) -> dict[str, Any]:
    """Return component scores and a combined rank for feed ordering."""
    significance = min(meaningful_changes * 12, 60)
    type_bonus = {
        "release": 35,
        "new_project": 30,
        "external_contribution": 28,
        "deep_work": 12,
        "exploration": 8,
        "routine": 4,
    }.get(activity_type or "routine", 4)
    significance += type_bonus

    tech_set = {canonical_key(t) for t in technologies}
    owner_keys = {canonical_key(t) for t in owner_techs}
    rising_keys = {canonical_key(t) for t in network_rising}
    overlap_owner = tech_set & owner_keys
    overlap_rising = tech_set & rising_keys
    relevance = len(overlap_owner) * 18 + len(overlap_rising) * 10
    if owner_techs and overlap_owner:
        relevance += 12

    novelty = 0
    if activity_type in ("new_project", "external_contribution", "exploration"):
        novelty += 20
    if trend_direction == "up":
        novelty += 12
    if activity_type == "external_contribution":
        novelty += 10

    conversation = 0
    if is_close:
        conversation += 22
    if activity_type in ("release", "external_contribution", "new_project"):
        conversation += 14
    if overlap_owner:
        conversation += 10

    why_bonus = 8 if has_why else 0
    total = significance + relevance + novelty + conversation + why_bonus

    return {
        "significance": significance,
        "relevance": relevance,
        "novelty": novelty,
        "conversation_potential": conversation,
        "total": total,
    }


def personal_note(
    *,
    technologies: list[str],
    owner_techs: set[str],
) -> str | None:
    """Single secondary personalization line for story cards."""
    tech_keys = {canonical_key(t) for t in technologies}
    owner_keys = {canonical_key(t) for t in owner_techs}
    if tech_keys & owner_keys:
        return "You also work in this area"
    return None
