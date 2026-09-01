from datetime import date

from app.network.facts import facts_from_loaded
from app.narrative.network_story import NetworkStoryOut, template_network_story, validate_network_story
from app.scoring.since import rank_score


def test_close_first_external_outranks_stranger_push():
    close_first = rank_score(significance=12, is_close=True, first_external=True, kind="first_external")
    stranger_push = rank_score(significance=1, is_close=False, kind="high_significance")
    assert close_first > stranger_push


def test_network_cluster_adds_ten():
    base = rank_score(significance=0, is_close=False, kind="other")
    cluster = rank_score(significance=0, is_close=False, kind="network_cluster")
    assert cluster - base == 10


def _base_facts(**overrides):
    week = date(2026, 9, 1)
    facts = facts_from_loaded(
        week_start=week,
        week_end=date(2026, 9, 7),
        owner_person_id=99,
        connections=[
            {"person_id": 1, "is_close": True},
            {"person_id": 2, "is_close": True},
            {"person_id": 3, "is_close": False},
            {"person_id": 4, "is_close": False},
            {"person_id": 5, "is_close": False},
            {"person_id": 99, "is_close": True},
        ],
        week_events=[
            {"id": 10, "person_id": 1, "event_type": "push", "metadata_": {"language": "python"}},
            {
                "id": 881,
                "person_id": 3,
                "event_type": "pull_request_merged",
                "repo_full_name": "org/repo",
                "metadata_": {"is_external": True},
            },
        ],
        prior_events=[
            {"id": 1, "person_id": 4, "event_type": "push", "metadata_": {"topics": ["jquery"]}},
            {"id": 2, "person_id": 5, "event_type": "push", "metadata_": {"topics": ["jquery"]}},
            {"id": 3, "person_id": 2, "event_type": "push", "metadata_": {"topics": ["jquery"]}},
        ],
        usernames={1: "alice", 2: "bob", 3: "sarah", 4: "dan", 5: "erin", 99: "me"},
        tech_this_week={
            "kubernetes": {1, 2, 3, 4},
            "vllm": {1, 5},
        },
        first_seen_by_person_tech={
            (1, "kubernetes"): week,
            (2, "kubernetes"): week,
            (3, "kubernetes"): date(2025, 1, 1),
            (4, "kubernetes"): date(2025, 1, 1),
            (1, "vllm"): week,
            (5, "vllm"): week,
        },
        tech_seen_before_week={"kubernetes"},
        **overrides,
    )
    return facts


def test_activity_direction_and_shared_repos():
    facts = facts_from_loaded(
        week_start=date(2026, 9, 1),
        week_end=date(2026, 9, 7),
        owner_person_id=99,
        connections=[
            {"person_id": 1, "is_close": False},
            {"person_id": 2, "is_close": False},
            {"person_id": 3, "is_close": False},
        ],
        week_events=[
            {"id": 1, "person_id": 1, "event_type": "push", "repo_full_name": "org/shared"},
            {"id": 2, "person_id": 1, "event_type": "push", "repo_full_name": "org/shared"},
            {"id": 3, "person_id": 2, "event_type": "push", "repo_full_name": "org/shared"},
        ],
        prior_events=[
            {"id": 9, "person_id": 2, "event_type": "push", "repo_full_name": "org/old"},
            {"id": 10, "person_id": 2, "event_type": "push", "repo_full_name": "org/old"},
            {"id": 11, "person_id": 2, "event_type": "push", "repo_full_name": "org/old"},
            {"id": 12, "person_id": 2, "event_type": "push", "repo_full_name": "org/old"},
        ],
        usernames={1: "a", 2: "b", 3: "c"},
        tech_this_week={},
        first_seen_by_person_tech={},
        tech_seen_before_week=set(),
        period_days=7,
    )
    assert facts["shared_repos"][0]["repo"] == "org/shared"
    assert facts["shared_repos"][0]["people_count"] == 2
    assert facts["activity_direction"][1]["direction"] == "up"
    assert facts["activity_direction"][1]["change_pct"] == 100
    assert "org/shared" in facts["activity_direction"][1]["new_repos"]
    assert 3 in facts["people_by_activity_level"]["quiet"]
    assert 1 in facts["people_by_activity_level"]["more_active"]


def test_rising_and_new_and_quiet_and_first_external():
    facts = _base_facts()
    assert facts["network_size"] == 5
    assert 2 in facts["quiet_close_person_ids"]
    assert 99 not in facts["active_person_ids"]
    rising_names = {r["name"] for r in facts["rising"]}
    assert "kubernetes" in rising_names
    new_names = {r["name"] for r in facts["new_in_network"]}
    assert "vllm" in new_names
    assert facts["first_external_oss"][0]["person_id"] == 3
    declining_names = {r["name"] for r in facts["declining"]}
    assert "jquery" in declining_names


def test_template_story_and_validation_rejects_hallucination():
    facts = _base_facts()
    usernames = {1: "alice", 2: "bob", 3: "sarah", 4: "dan", 5: "erin"}
    templated = template_network_story(facts, usernames)
    assert validate_network_story(templated, facts, usernames)
    bad = NetworkStoryOut(
        headline="Pivot",
        bullets=["They are pivoting to cobol"],
        cited_person_ids=[1],
        cited_techs=["cobol"],
    )
    assert not validate_network_story(bad, facts, usernames)
    unknown_person = NetworkStoryOut(
        headline="Hi",
        bullets=["hello"],
        cited_person_ids=[999],
        cited_techs=["kubernetes"],
    )
    assert not validate_network_story(unknown_person, facts, usernames)
