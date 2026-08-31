import pytest
from datetime import datetime, timezone
from app.github.normalize import normalize_event

def test_normalize_push_event():
    raw_event = {
        "id": "123",
        "type": "PushEvent",
        "repo": {"name": "owner/repo"},
        "created_at": "2023-01-01T12:00:00Z",
        "payload": {}
    }
    result = normalize_event(raw_event, person_id=1)
    assert result is not None
    assert result["event_type"] == "push"
    assert result["external_event_id"] == "123"

def test_normalize_create_repo_event():
    raw_event = {
        "id": "124",
        "type": "CreateEvent",
        "repo": {"name": "owner/repo"},
        "created_at": "2023-01-01T12:00:00Z",
        "payload": {"ref_type": "repository"}
    }
    result = normalize_event(raw_event, person_id=1)
    assert result is not None
    assert result["event_type"] == "repository_created"

def test_normalize_pr_opened():
    raw_event = {
        "id": "125",
        "type": "PullRequestEvent",
        "repo": {"name": "owner/repo"},
        "created_at": "2023-01-01T12:00:00Z",
        "payload": {"action": "opened"}
    }
    result = normalize_event(raw_event, person_id=1)
    assert result is not None
    assert result["event_type"] == "pull_request_opened"

def test_normalize_pr_merged():
    raw_event = {
        "id": "126",
        "type": "PullRequestEvent",
        "repo": {"name": "owner/repo"},
        "created_at": "2023-01-01T12:00:00Z",
        "payload": {"action": "closed", "pull_request": {"merged": True}}
    }
    result = normalize_event(raw_event, person_id=1)
    assert result is not None
    assert result["event_type"] == "pull_request_merged"

def test_normalize_pr_closed_unmerged():
    raw_event = {
        "id": "127",
        "type": "PullRequestEvent",
        "repo": {"name": "owner/repo"},
        "created_at": "2023-01-01T12:00:00Z",
        "payload": {"action": "closed", "pull_request": {"merged": False}}
    }
    result = normalize_event(raw_event, person_id=1)
    assert result is None

def test_normalize_pr_merged_via_merged_at():
    raw_event = {
        "id": "129",
        "type": "PullRequestEvent",
        "repo": {"name": "org/repo"},
        "created_at": "2023-01-01T12:00:00Z",
        "payload": {"action": "closed", "pull_request": {"merged": False, "merged_at": "2023-01-01T12:01:00Z"}},
    }
    result = normalize_event(raw_event, person_id=1)
    assert result is not None
    assert result["event_type"] == "pull_request_merged"

def test_normalize_ignored_event():
    raw_event = {
        "id": "128",
        "type": "WatchEvent",
        "repo": {"name": "owner/repo"},
        "created_at": "2023-01-01T12:00:00Z",
        "payload": {"action": "started"}
    }
    result = normalize_event(raw_event, person_id=1)
    assert result is None
