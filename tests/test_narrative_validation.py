import pytest
from app.narrative.schema import WeeklyNarrative
from app.narrative.generate import passes_grounding_check

def test_rejects_ungrounded_technology():
    output = WeeklyNarrative(
        narrative="Ahmed has been building a Rust game engine.",
        technologies_mentioned=["rust"],
        supporting_event_ids=[101, 102],
    )
    assert not passes_grounding_check(
        output, 
        allowed_technologies={"python", "docker"}, 
        allowed_event_ids={101, 102}
    )

def test_rejects_ungrounded_event():
    output = WeeklyNarrative(
        narrative="She opened a new PR.",
        technologies_mentioned=["python"],
        supporting_event_ids=[999],
    )
    assert not passes_grounding_check(
        output, 
        allowed_technologies={"python"}, 
        allowed_event_ids={101, 102}
    )

def test_passes_valid_output():
    output = WeeklyNarrative(
        narrative="She opened a new PR in a Python repo.",
        technologies_mentioned=["python"],
        supporting_event_ids=[101],
    )
    assert passes_grounding_check(
        output, 
        allowed_technologies={"python", "docker"}, 
        allowed_event_ids={101, 102}
    )
