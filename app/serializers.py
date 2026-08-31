from datetime import date, datetime
from typing import Any

from app.models.activity_event import ActivityEvent
from app.models.connection import Connection
from app.models.insight import Insight
from app.models.owner import Owner
from app.models.person import Person


def _iso(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def owner_to_dict(owner: Owner) -> dict[str, Any]:
    return {
        "id": owner.id,
        "label": owner.label,
        "github_username": owner.github_username,
        "delivery_email": owner.delivery_email,
        "is_active": owner.is_active,
        "created_at": _iso(owner.created_at),
    }


def insight_to_dict(insight: Insight | None) -> dict[str, Any] | None:
    if insight is None:
        return None
    return {
        "id": insight.id,
        "person_id": insight.person_id,
        "week_start": _iso(insight.week_start),
        "week_end": _iso(insight.week_end),
        "narrative_text": insight.narrative_text,
        "supporting_event_ids": insight.supporting_event_ids,
        "significance_total": insight.significance_total,
        "model_used": insight.model_used,
        "generated_at": _iso(insight.generated_at),
    }


def event_to_dict(event: ActivityEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "person_id": event.person_id,
        "source": event.source,
        "external_event_id": event.external_event_id,
        "event_type": event.event_type,
        "repo_full_name": event.repo_full_name,
        "occurred_at": _iso(event.occurred_at),
        "significance_score": event.significance_score,
        "metadata": event.metadata_,
    }


def person_card_dict(person: Person, *, is_close: bool, insight: Insight | None) -> dict[str, Any]:
    return {
        "id": person.id,
        "github_username": person.github_username,
        "display_name": person.display_name,
        "avatar_url": person.avatar_url,
        "is_close": is_close,
        "latest_insight": insight_to_dict(insight),
    }


def connection_to_dict(conn: Connection) -> dict[str, Any]:
    person = conn.person
    return {
        "id": conn.id,
        "owner_id": conn.owner_id,
        "person_id": conn.person_id,
        "is_close": conn.is_close,
        "added_at": _iso(conn.added_at),
        "person": {
            "id": person.id,
            "github_username": person.github_username,
            "display_name": person.display_name,
            "avatar_url": person.avatar_url,
        },
    }
