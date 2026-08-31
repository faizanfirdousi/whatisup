from typing import Any

def score_event(event: dict[str, Any], context: dict[str, Any] = None) -> int:
    """
    Deterministically score a normalized activity event for significance.
    Expects event dict like the one returned from normalize_event,
    with an additional context dict if needed (e.g., is_first_repo).
    """
    if context is None:
        context = {}
        
    event_type = event.get("event_type")
    payload = event.get("raw_payload", {}).get("payload", {})
    
    if event_type == "repository_created":
        if context.get("is_first_repo", False):
            return 15
        return 5
        
    if event_type == "pull_request_merged":
        if context.get("is_external", False):
            return 12
        return 5  # Internal PR merged
        
    if event_type == "pull_request_opened":
        if context.get("is_external", False):
            return 10
        return 3
        
    if event_type == "release_published":
        return 8

    if event_type == "pull_request_reviewed":
        return 4 if context.get("is_external", False) else 2

    if event_type == "tag_created":
        return 3

    if event_type == "push":
        # Check commit messages for routine bumps/typos
        commits = payload.get("commits", [])
        is_routine = False
        if commits:
            # Simple heuristic: if all commits are routine, it's routine
            routine_keywords = ["bump", "typo", "fix readme", "update deps"]
            all_routine = True
            for commit in commits:
                msg = commit.get("message", "").lower()
                if not any(k in msg for k in routine_keywords):
                    all_routine = False
                    break
            if all_routine:
                return 0
        return 1
        
    # Other tracked events like fork, issue_opened
    if event_type in ["fork", "issue_opened"]:
        return 2

    return 0
