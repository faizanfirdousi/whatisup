from app.narrative.template import template_narrative, template_narrative_enriched


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


def test_enriched_template_is_a_story_not_a_counter():
    enriched = template_narrative_enriched(
        {"github_username": "alice", "display_name": "Alice"},
        [
            {
                "id": 1,
                "event_type": "pull_request_opened",
                "repo_full_name": "kserve/kserve",
                "significance_score": 10,
                "metadata_": {"is_external": True, "language": "python"},
            }
        ],
        [{"name": "python", "confidence": 1.0}],
    )
    assert enriched["headline"]
    assert "opened 1" not in enriched["narrative"].lower()
    assert "kserve" in enriched["narrative"].lower() or "python" in enriched["narrative"].lower()
    assert enriched["activity_type"] == "external_contribution"
    assert "beyond their own repository" in enriched["why_it_matters"].lower()


def test_external_why_it_matters_uses_repo_context():
    enriched = template_narrative_enriched(
        {"github_username": "saiyam", "display_name": "Saiyam"},
        [
            {
                "id": 1,
                "event_type": "pull_request_opened",
                "repo_full_name": "srelens/srelens",
                "significance_score": 10,
                "metadata_": {"is_external": True, "language": "typescript"},
            }
        ],
        [{"name": "typescript", "confidence": 1.0}],
    )
    assert "srelens/srelens" in enriched["why_it_matters"]
    assert "beyond their own repository" in enriched["why_it_matters"].lower()


def test_release_why_it_matters_is_release_specific():
    enriched = template_narrative_enriched(
        {"github_username": "alice", "display_name": "Alice"},
        [
            {
                "id": 1,
                "event_type": "release_published",
                "repo_full_name": "alice/tool",
                "significance_score": 12,
                "metadata_": {"language": "go"},
            },
            {
                "id": 2,
                "event_type": "pull_request_opened",
                "repo_full_name": "other/tool",
                "significance_score": 8,
                "metadata_": {"is_external": True},
            },
        ],
        [{"name": "go", "confidence": 1.0}],
    )
    assert enriched["activity_type"] == "release"
    assert "release" in enriched["why_it_matters"].lower()
    assert "external contribution" not in enriched["why_it_matters"].lower()
