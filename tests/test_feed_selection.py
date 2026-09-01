"""Tests for diverse feed selection."""

from app.network.feed_selection import select_diverse_stories


def _story(
    person_id: int,
    activity_type: str,
    rank: int,
    *,
    primary_tech: str | None = None,
    repo_ecosystem: str | None = None,
    is_tech_shift: bool = False,
    personal_note: str | None = None,
    relevance: int = 0,
) -> dict:
    return {
        "id": f"story:{person_id}",
        "person": {"id": person_id, "github_username": f"user{person_id}"},
        "activity_type": activity_type,
        "rank": rank,
        "primary_tech": primary_tech,
        "repo_ecosystem": repo_ecosystem,
        "is_tech_shift": is_tech_shift,
        "personal_note": personal_note,
        "relevance": relevance,
    }


def test_limits_external_contributions_to_one_when_other_types_exist():
    stories = [
        _story(1, "external_contribution", 200, primary_tech="go", repo_ecosystem="k8s"),
        _story(2, "external_contribution", 190, primary_tech="go", repo_ecosystem="k8s"),
        _story(3, "external_contribution", 180, primary_tech="python", repo_ecosystem="pytorch"),
        _story(4, "external_contribution", 170, primary_tech="rust", repo_ecosystem="rust-lang"),
        _story(5, "release", 160, primary_tech="go", repo_ecosystem="acme"),
        _story(6, "new_project", 150, primary_tech="typescript", repo_ecosystem="acme"),
    ]
    picked = select_diverse_stories(stories, limit=5)
    external = [s for s in picked if s["activity_type"] == "external_contribution"]
    types = {s["activity_type"] for s in picked}

    assert len(external) == 1
    assert external[0]["person"]["id"] == 1
    assert "release" in types
    assert "new_project" in types
    assert len(types) == len(picked)


def test_prefers_different_activity_types_over_same_rank_duplicates():
    stories = [
        _story(1, "external_contribution", 100),
        _story(2, "external_contribution", 99),
        _story(3, "external_contribution", 98),
        _story(4, "release", 50),
        _story(5, "new_project", 40),
    ]
    picked = select_diverse_stories(stories, limit=3)
    assert len(picked) == 3
    assert len({s["activity_type"] for s in picked}) == 3


def test_mmr_penalizes_same_repo_ecosystem_on_fill():
    stories = [
        _story(1, "external_contribution", 100, repo_ecosystem="kubernetes"),
        _story(2, "release", 90, repo_ecosystem="kubernetes"),
        _story(3, "deep_work", 80, repo_ecosystem="acme"),
        _story(4, "exploration", 70, repo_ecosystem="other"),
    ]
    picked = select_diverse_stories(stories, limit=4)
    assert picked[0]["person"]["id"] == 1
    assert any(s["person"]["id"] == 3 for s in picked)
