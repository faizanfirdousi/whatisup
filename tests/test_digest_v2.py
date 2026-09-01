from datetime import date
from types import SimpleNamespace

from app.network.facts import facts_from_loaded, get_period_bounds
from app.routers.digest_v2 import build_digest_payload


def test_period_bounds_default_to_7d():
    start, end, start_dt, end_dt = get_period_bounds("nope")
    assert (end - start).days == 6
    assert start_dt.tzinfo is not None
    assert end_dt >= start_dt


def _event(person_id, **kwargs):
    defaults = {
        "id": person_id * 10,
        "person_id": person_id,
        "event_type": "push",
        "repo_full_name": "alice/app",
        "significance_score": 1,
        "metadata_": {},
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_digest_v2_uses_stories_not_raw_scores():
    facts = facts_from_loaded(
        week_start=date(2026, 8, 27),
        week_end=date(2026, 9, 2),
        owner_person_id=99,
        connections=[
            {"person_id": 1, "is_close": True},
            {"person_id": 2, "is_close": False},
        ],
        week_events=[
            {
                "id": 1,
                "person_id": 1,
                "event_type": "release_published",
                "repo_full_name": "alice/memwarden",
                "metadata_": {"language": "go"},
            },
            {
                "id": 2,
                "person_id": 2,
                "event_type": "pull_request_opened",
                "repo_full_name": "kserve/kserve",
                "metadata_": {"is_external": True, "language": "python"},
            },
        ],
        prior_events=[],
        usernames={1: "alice", 2: "atharva"},
        tech_this_week={"go": {1}, "python": {2}},
        first_seen_by_person_tech={},
        tech_seen_before_week=set(),
    )
    payload = build_digest_payload(
        owner_name="Faizan",
        period="7d",
        rows=[
            {
                "connection_id": 10,
                "is_close": True,
                "person": {
                    "id": 1,
                    "github_username": "alice",
                    "display_name": "Alice",
                    "avatar_url": None,
                },
                "events": [
                    _event(
                        1,
                        event_type="release_published",
                        repo_full_name="alice/memwarden",
                        significance_score=12,
                    )
                ],
                "insight": None,
            },
            {
                "connection_id": 11,
                "is_close": False,
                "person": {
                    "id": 2,
                    "github_username": "atharva",
                    "display_name": "Atharva",
                    "avatar_url": None,
                },
                "events": [
                    _event(
                        2,
                        event_type="pull_request_opened",
                        repo_full_name="kserve/kserve",
                        significance_score=10,
                        metadata_={"is_external": True, "language": "python"},
                    )
                ],
                "insight": None,
            },
        ],
        facts=facts,
    )

    assert "significance_total" not in payload
    assert payload["summary"]["people_shipped"] == 1
    assert payload["summary"]["meaningful_changes"] == 2
    assert len(payload["stories"]) == 2
    assert all("significance_total" not in story for story in payload["stories"])
    headlines = " ".join(story["headline"] for story in payload["stories"]).lower()
    assert "alice" in headlines or "atharva" in headlines
    assert payload["close_circle"][0]["person"]["github_username"] == "alice"
    assert payload["network_pulse"]["network_size"] == 2
    assert {row["person"]["id"] for row in payload["people"]} == {1, 2}
