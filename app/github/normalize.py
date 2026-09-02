from datetime import datetime
from typing import Any
from dateutil import parser
import logging

from app.github.work_signals import extract_work_signals

logger = logging.getLogger(__name__)


def parse_github_date(date_str: str) -> datetime:
    """Parse GitHub ISO format date to Python datetime."""
    return parser.isoparse(date_str)


def normalize_event(raw_event: dict[str, Any], person_id: int) -> dict[str, Any] | None:
    """
    Map raw GitHub event to normalized ActivityEvent dictionary.
    Returns None if the event type is not tracked.
    """
    gh_type = raw_event.get("type")
    payload = raw_event.get("payload", {})
    
    event_type = None
    
    # Mapping logic per PRD 9.2
    if gh_type == "PushEvent":
        event_type = "push"
    elif gh_type == "CreateEvent" and payload.get("ref_type") == "repository":
        event_type = "repository_created"
    elif gh_type == "PullRequestEvent":
        action = payload.get("action")
        pr = payload.get("pull_request") or {}
        merged = bool(pr.get("merged") or pr.get("merged_at"))
        if action == "opened":
            event_type = "pull_request_opened"
        elif action == "closed" and merged:
            event_type = "pull_request_merged"
    elif gh_type == "PullRequestReviewEvent":
        event_type = "pull_request_reviewed"
    elif gh_type == "CreateEvent" and payload.get("ref_type") == "tag":
        event_type = "tag_created"
    elif gh_type == "IssuesEvent" and payload.get("action") == "opened":
        event_type = "issue_opened"
    elif gh_type == "ReleaseEvent" and payload.get("action") == "published":
        event_type = "release_published"
    elif gh_type == "ForkEvent":
        event_type = "fork"
        
    if not event_type:
        return None
        
    repo_name = raw_event.get("repo", {}).get("name")
    
    return {
        "person_id": person_id,
        "source": "github",
        "external_event_id": raw_event.get("id"),
        "event_type": event_type,
        "repo_full_name": repo_name,
        "occurred_at": parse_github_date(raw_event.get("created_at")),
        "raw_payload": raw_event,
        "metadata_": extract_work_signals(raw_event),
        "significance_score": 0, # To be filled by scoring pass
    }
