"""Merge duplicate technology rows onto canonical keys."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.technology import PersonTechnology, Technology
from app.scoring.canonical import canonical_key


async def backfill_canonical_technologies(session: AsyncSession) -> dict[str, int]:
    """Merge alias technology rows (golang, agentic, …) onto canonical keys (go, ai-agents)."""
    stats = {"groups_merged": 0, "rows_repointed": 0, "aliases_removed": 0, "renamed": 0}

    res = await session.execute(select(Technology))
    all_techs = list(res.scalars().all())
    groups: dict[str, list[Technology]] = defaultdict(list)
    for tech in all_techs:
        groups[canonical_key(tech.name)].append(tech)

    for key, techs in groups.items():
        if len(techs) == 1 and techs[0].name == key:
            continue

        stats["groups_merged"] += 1
        canonical_row = next((t for t in techs if t.name == key), None)
        if canonical_row is None:
            canonical_row = min(techs, key=lambda t: t.id)
            if canonical_row.name != key:
                canonical_row.name = key
                stats["renamed"] += 1

        for duplicate in techs:
            if duplicate.id == canonical_row.id:
                continue

            pt_res = await session.execute(
                select(PersonTechnology).where(PersonTechnology.technology_id == duplicate.id)
            )
            for pt in pt_res.scalars().all():
                existing_res = await session.execute(
                    select(PersonTechnology).where(
                        PersonTechnology.person_id == pt.person_id,
                        PersonTechnology.technology_id == canonical_row.id,
                    )
                )
                existing = existing_res.scalar_one_or_none()
                if existing:
                    existing.confidence = max(existing.confidence, pt.confidence)
                    if pt.first_seen_at and (
                        not existing.first_seen_at or pt.first_seen_at < existing.first_seen_at
                    ):
                        existing.first_seen_at = pt.first_seen_at
                    if pt.last_seen_at and (
                        not existing.last_seen_at or pt.last_seen_at > existing.last_seen_at
                    ):
                        existing.last_seen_at = pt.last_seen_at
                    await session.delete(pt)
                else:
                    pt.technology_id = canonical_row.id
                    stats["rows_repointed"] += 1

            await session.delete(duplicate)
            stats["aliases_removed"] += 1

    await session.flush()
    return stats
