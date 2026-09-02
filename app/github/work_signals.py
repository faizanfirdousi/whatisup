"""Evidence extracted from GitHub event payloads (titles, commit subjects, work kinds)."""

from __future__ import annotations

import re
from typing import Any

_KIND_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tests", re.compile(r"\b(tests?|specs?|pytest|unittest|e2e|coverage)\b", re.I)),
    ("docs", re.compile(r"\b(docs?|readme|documentation|changelog)\b", re.I)),
    ("ci", re.compile(r"\b(ci|cd|github actions|workflow|pipeline)\b", re.I)),
    ("infra", re.compile(r"\b(docker(?:file)?|k8s|kubernetes|terraform|helm|infra)\b", re.I)),
    ("fix", re.compile(r"\b(fix(?:es|ed)?|bugfix|hotfix|bug)\b", re.I)),
    ("refactor", re.compile(r"\b(refactor(?:ed|ing)?|cleanup|clean[- ]up)\b", re.I)),
]


def detect_work_kinds(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for kind, pattern in _KIND_PATTERNS:
        if pattern.search(text) and kind not in found:
            found.append(kind)
    return found


def extract_work_signals(raw_event: dict[str, Any] | None) -> dict[str, Any]:
    """Compact, evidence-bearing fields from a GitHub events API payload."""
    if not raw_event:
        return {}
    payload = raw_event.get("payload") or {}
    titles: list[str] = []
    subjects: list[str] = []

    pr = payload.get("pull_request") or {}
    if isinstance(pr, dict) and pr.get("title"):
        titles.append(str(pr["title"]).strip()[:200])

    issue = payload.get("issue") or {}
    if isinstance(issue, dict) and issue.get("title"):
        titles.append(str(issue["title"]).strip()[:200])

    release = payload.get("release") or {}
    if isinstance(release, dict):
        label = (release.get("name") or release.get("tag_name") or "").strip()
        if label:
            titles.append(label[:200])

    for commit in (payload.get("commits") or [])[:8]:
        if not isinstance(commit, dict):
            continue
        msg = (commit.get("message") or "").split("\n", 1)[0].strip()
        if msg:
            subjects.append(msg[:160])

    kinds: list[str] = []
    for text in titles + subjects:
        for kind in detect_work_kinds(text):
            if kind not in kinds:
                kinds.append(kind)

    out: dict[str, Any] = {}
    if titles:
        out["titles"] = titles[:3]
    if subjects:
        out["commit_subjects"] = subjects[:5]
    if kinds:
        out["work_kinds"] = kinds
    return out
