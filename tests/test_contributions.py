from app.github.work_signals import detect_work_kinds, extract_work_signals
from app.narrative.contributions import build_contribution_digest
from app.narrative.template import template_narrative_enriched


def test_detects_test_work_from_title():
    assert "tests" in detect_work_kinds("Add e2e tests for inference")
    assert detect_work_kinds("Bump dependencies") == []


def test_extracts_pr_title_from_github_payload():
    signals = extract_work_signals(
        {
            "type": "PullRequestEvent",
            "payload": {"action": "opened", "pull_request": {"title": "Add unit tests for scheduler"}},
        }
    )
    assert signals["titles"] == ["Add unit tests for scheduler"]
    assert "tests" in signals["work_kinds"]


def test_digest_prefers_contribution_over_language():
    digest = build_contribution_digest(
        {"github_username": "alice"},
        [
            {
                "id": 1,
                "event_type": "pull_request_opened",
                "repo_full_name": "kserve/kserve",
                "metadata_": {
                    "is_external": True,
                    "language": "go",
                    "titles": ["Add e2e tests for inference"],
                    "work_kinds": ["tests"],
                    "description": "Serverless Inferencing on Kubernetes",
                },
            }
        ],
    )
    assert digest["primary_kind"] == "tests"
    assert "kserve/kserve" in digest["summary_points"][0]
    assert "writing tests" in digest["summary_points"][0]


def test_enriched_insight_is_about_the_work_not_the_stack():
    enriched = template_narrative_enriched(
        {"github_username": "alice", "display_name": "Alice"},
        [
            {
                "id": 1,
                "event_type": "pull_request_opened",
                "repo_full_name": "kserve/kserve",
                "significance_score": 10,
                "metadata_": {
                    "is_external": True,
                    "language": "go",
                    "titles": ["Add e2e tests for inference"],
                    "work_kinds": ["tests"],
                },
            }
        ],
        [{"name": "go", "confidence": 1.0}],
    )
    assert "Wrote tests" in enriched["headline"]
    assert "kserve" in enriched["headline"].lower()
    assert "go" not in enriched["headline"].lower()
    assert "writing tests" in enriched["narrative"]
    assert "Add e2e tests for inference" in enriched["narrative"]
    assert "focus on go" not in enriched["narrative"].lower()
    assert enriched["focus_area"] == "testing"
    assert "writing tests" in enriched["why_it_matters"]
