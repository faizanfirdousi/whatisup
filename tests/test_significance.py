import pytest
from app.scoring.significance import score_event

def make_event(event_type: str, commit_message: str = None) -> dict:
    event = {
        "event_type": event_type,
        "raw_payload": {"payload": {}}
    }
    if commit_message:
        event["raw_payload"]["payload"]["commits"] = [{"message": commit_message}]
    return event

def test_new_repository_created():
    assert score_event(make_event("repository_created")) == 5

def test_first_repository_ever():
    assert score_event(make_event("repository_created"), context={"is_first_repo": True}) == 15

def test_external_pr_merged():
    assert score_event(make_event("pull_request_merged"), context={"is_external": True}) == 12

def test_dependency_bump_scores_zero():
    assert score_event(make_event("push", commit_message="bump lodash to 4.17.21")) == 0

def test_normal_push_scores_one():
    assert score_event(make_event("push", commit_message="add new auth middleware")) == 1

def test_external_pr_opened():
    assert score_event(make_event("pull_request_opened"), context={"is_external": True}) == 10

def test_internal_pr_opened():
    assert score_event(make_event("pull_request_opened")) == 3


def test_week_bounds_are_timezone_aware():
    from datetime import timezone
    from app.pipeline import current_week_bounds, build_score_context

    week_start, week_end, start_dt, end_dt = current_week_bounds()
    assert start_dt.tzinfo is timezone.utc
    assert end_dt.tzinfo is timezone.utc
    assert week_end >= week_start


class _Person:
    github_username = "alice"


def test_external_repo_context():
    from app.pipeline import build_score_context

    event = {"event_type": "pull_request_opened", "repo_full_name": "kubernetes/kubernetes"}
    ctx = build_score_context(event, _Person(), has_existing_repo=True)
    assert ctx.get("is_external") is True

    event = {"event_type": "push", "repo_full_name": "alice/dotfiles"}
    ctx = build_score_context(event, _Person(), has_existing_repo=True)
    assert ctx.get("is_external") is None
