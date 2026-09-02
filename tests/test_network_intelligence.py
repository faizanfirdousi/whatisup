from datetime import date

from app.network.facts import facts_from_loaded
from app.network.intelligence import (
    build_network_intelligence,
    infer_focus,
    technology_movement,
)


def _facts(**overrides):
    base = {
        "week_start": date(2026, 9, 1),
        "week_end": date(2026, 9, 7),
        "owner_person_id": 99,
        "connections": [
            {"person_id": 1, "is_close": True},
            {"person_id": 2, "is_close": False},
            {"person_id": 3, "is_close": False},
            {"person_id": 4, "is_close": False},
        ],
        "week_events": [],
        "prior_events": [
            {"id": 1, "person_id": 2, "event_type": "push", "metadata_": {"language": "typescript"}},
            {"id": 2, "person_id": 3, "event_type": "push", "metadata_": {"language": "typescript"}},
            {"id": 3, "person_id": 4, "event_type": "push", "metadata_": {"language": "go"}},
            {"id": 4, "person_id": 4, "event_type": "push", "metadata_": {"language": "go"}},
        ],
        "usernames": {1: "a", 2: "b", 3: "c", 4: "d"},
        "tech_this_week": {
            "go": {1, 2, 3, 4},
            "kubernetes": {1, 2, 3},
            "typescript": {2, 3},
            "vllm": {2, 3},
        },
        "first_seen_by_person_tech": {
            (2, "vllm"): date(2026, 9, 1),
            (3, "vllm"): date(2026, 9, 2),
        },
        "tech_seen_before_week": {"go", "kubernetes", "typescript"},
    }
    base.update(overrides)
    return facts_from_loaded(**base)


def test_technology_movement_splits_established_growing_and_new():
    facts = _facts()
    movement = technology_movement(facts)

    established = {row["name"] for row in movement["established"]}
    growing = {row["name"] for row in movement["growing"]}
    new = {row["name"] for row in movement["new"]}

    assert "typescript" in established
    assert any(row.get("delta_people", 0) >= 0 for row in movement["growing"])
    assert "vllm" in new


def test_build_network_intelligence_has_hero_and_curated_story():
    facts = _facts(
        week_events=[
            {
                "id": 10,
                "person_id": 1,
                "event_type": "push",
                "repo_full_name": "org/shared",
                "metadata_": {"language": "go"},
            },
            {
                "id": 11,
                "person_id": 2,
                "event_type": "push",
                "repo_full_name": "org/shared",
                "metadata_": {"language": "go"},
            },
        ],
    )
    payload = build_network_intelligence(
        facts,
        usernames={1: "a", 2: "b", 3: "c", 4: "d"},
        owner_techs={"go"},
        owner_focus="go projects",
    )

    assert "strongest active theme" in payload["hero"]["headline"].lower()
    assert payload["hero"]["cta"]["label"].startswith("Explore ")
    assert payload["hero"]["signals"] == []
    assert all("spreading" not in s["title"].lower() for s in payload["story"]["stories"])
    assert payload["story"]["stories"]
    assert all("recent activity involving" in s["body"].lower() for s in payload["story"]["stories"])
    assert payload["technology_movement"]["established"]
    assert isinstance(payload["clusters"], list)
    assert payload.get("for_you") is not None
    assert "direction" not in (payload.get("for_you") or {})


def test_hero_has_single_cta_not_tech_chips():
    facts = _facts()
    payload = build_network_intelligence(
        facts,
        usernames={1: "a", 2: "b", 3: "c", 4: "d"},
        owner_techs={"go"},
    )
    assert payload["hero"]["cta"]["href"] == "/network"
    assert payload["hero"]["signals"] == []


def test_infer_focus_uses_repos_when_no_focus_area():
    focus = infer_focus(None, ["go"], ["acme/platform"])
    assert focus == "go work in platform"

    assert infer_focus(None, [], []) is None
