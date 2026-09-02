"""Tests for canonical technology backfill logic."""

from app.scoring.canonical import canonical_key


def test_canonical_key_collapses_golang():
    assert canonical_key("golang") == canonical_key("go") == "go"


def test_canonical_key_collapses_agentic_aliases():
    keys = {canonical_key(alias) for alias in ("agentic", "ai-agent", "ai-agents")}
    assert keys == {"ai-agents"}
