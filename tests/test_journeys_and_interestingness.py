from datetime import date, datetime, timezone

from app.network.journeys import build_monthly_phases, detect_milestones, journey_hook
from app.network.interestingness import compute_interestingness, personal_note


def test_build_monthly_phases_groups_by_month():
    events = [
        {
            "event_type": "push",
            "repo_full_name": "alice/app",
            "occurred_at": datetime(2026, 6, 10, tzinfo=timezone.utc),
            "metadata_": {"language": "python"},
        },
        {
            "event_type": "push",
            "repo_full_name": "alice/app",
            "occurred_at": datetime(2026, 7, 12, tzinfo=timezone.utc),
            "metadata_": {"language": "docker"},
        },
    ]
    phases = build_monthly_phases(events, github_username="alice")
    assert len(phases) == 2
    assert phases[0]["month"] == "July"
    assert "docker" in phases[0]["summary"].lower() or "Docker" in str(phases[0]["technologies"])


def test_detect_milestones_finds_first_external_pr():
    events = [
        {
            "event_type": "pull_request_opened",
            "repo_full_name": "k8s/kubernetes",
            "occurred_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
            "metadata_": {"is_external": True},
        }
    ]
    milestones = detect_milestones(events, github_username="alice")
    kinds = {m["kind"] for m in milestones}
    assert "first_external_pr" in kinds


def test_journey_hook_detects_shift():
    phases = [
        {"month": "August", "summary": "Contributed to external open-source projects", "technologies": ["go"]},
        {"month": "June", "summary": "Mostly working on python projects", "technologies": ["python"]},
    ]
    hook = journey_hook(phases)
    assert hook is not None
    assert "python" in hook.lower() or "go" in hook.lower()


def test_interestingness_boosts_close_circle_overlap():
    close = compute_interestingness(
        activity_type="external_contribution",
        meaningful_changes=1,
        technologies=["kubernetes"],
        is_close=True,
        owner_techs={"kubernetes"},
        network_rising={"kubernetes"},
        trend_direction="up",
        has_why=True,
    )
    distant = compute_interestingness(
        activity_type="external_contribution",
        meaningful_changes=1,
        technologies=["kubernetes"],
        is_close=False,
        owner_techs=set(),
        network_rising=set(),
        trend_direction="steady",
        has_why=False,
    )
    assert close["total"] > distant["total"]
    assert close["relevance"] > 0


def test_personal_note_requires_strong_overlap():
    assert personal_note(technologies=["go", "helm"], owner_techs={"golang"}) is None
    note = personal_note(technologies=["go", "kubernetes", "helm"], owner_techs={"golang", "kubernetes"})
    assert note is not None
    assert "Strong overlap" in note
    assert "Go" in note or "Kubernetes" in note
