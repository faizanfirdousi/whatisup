from app.narrative.network_story import NetworkStoryOut, validate_network_story


FACTS = {
    "active_person_ids": [1],
    "quiet_close_person_ids": [],
    "tech_this_week": [{"name": "kubernetes", "person_ids": [1], "new_to_person_ids": []}],
    "rising": [{"name": "kubernetes", "this_week_people": 5, "prior_4w_avg_people": 1.2}],
    "new_in_network": [],
    "first_external_oss": [],
}


def test_unknown_tech_rejected():
    out = NetworkStoryOut(
        headline="x",
        bullets=["a", "b", "c"],
        cited_person_ids=[1],
        cited_techs=["made-up-lang"],
    )
    assert not validate_network_story(out, FACTS, {1: "alice"})


def test_unknown_person_rejected():
    out = NetworkStoryOut(
        headline="x",
        bullets=["a", "b", "c"],
        cited_person_ids=[42],
        cited_techs=["kubernetes"],
    )
    assert not validate_network_story(out, FACTS, {1: "alice"})


def test_unknown_handle_in_prose_rejected():
    out = NetworkStoryOut(
        headline="x",
        bullets=["shoutout to @not-in-network"],
        cited_person_ids=[1],
        cited_techs=["kubernetes"],
    )
    assert not validate_network_story(out, FACTS, {1: "alice"})
