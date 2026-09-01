"""Tests for technology canonicalization."""

from app.scoring.canonical import canonical_key, display_name
from app.scoring.technology import extract_technologies


def test_golang_maps_to_go():
    assert canonical_key("golang") == "go"
    assert display_name("golang") == "Go"


def test_agentic_aliases_merge():
    for alias in ("agentic", "ai-agent", "ai-agents", "agentic-ai"):
        assert canonical_key(alias) == "ai-agents"
    assert display_name("agentic") == "AI Agents"


def test_extract_technologies_canonicalizes_language():
    techs = extract_technologies({"language": "Golang"})
    assert techs[0]["name"] == "go"
