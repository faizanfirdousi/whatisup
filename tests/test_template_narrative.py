from app.narrative.template import template_narrative


def test_template_mentions_prs_and_repos():
    text, ids, model = template_narrative(
        {"github_username": "alice", "display_name": "Alice"},
        [
            {"id": 1, "event_type": "pull_request_opened", "repo_full_name": "org/tool", "significance_score": 10},
            {"id": 2, "event_type": "push", "repo_full_name": "alice/app", "significance_score": 1},
            {"id": 3, "event_type": "push", "repo_full_name": "alice/app", "significance_score": 1},
        ],
        [{"name": "python"}],
    )
    assert "Alice" in text
    assert "PR" in text
    assert "org/tool" in text or "alice/app" in text
    assert ids == [1, 2, 3]
    assert model == "template"
    assert "routine" not in text.lower()
