from typing import Any
import httpx
import logging

from app.github.client import github_client

logger = logging.getLogger(__name__)


async def fetch_user(username: str) -> dict[str, Any]:
    """Fetch a GitHub user profile. Raises if the user does not exist."""
    response = await github_client.get(f"/users/{username}")
    return response.json()


async def fetch_following(username: str) -> list[dict[str, Any]]:
    """Fetch all users a given GitHub user is following (handles pagination)."""
    following: list[dict[str, Any]] = []
    page = 1

    while True:
        response = await github_client.get(
            f"/users/{username}/following",
            params={"per_page": 100, "page": page},
        )
        data = response.json()
        if not data:
            break
        following.extend(data)

        link_header = response.headers.get("link", "")
        if 'rel="next"' not in link_header:
            break
        page += 1

    return following


async def fetch_public_events(username: str, pages: int = 2) -> list[dict[str, Any]]:
    """Fetch public events for a user. Defaults to 2 pages (200 events)."""
    events: list[dict[str, Any]] = []

    for page in range(1, pages + 1):
        try:
            response = await github_client.get(
                f"/users/{username}/events/public",
                params={"per_page": 100, "page": page},
            )
            data = response.json()
            if not data:
                break
            events.extend(data)

            link_header = response.headers.get("link", "")
            if 'rel="next"' not in link_header:
                break
        except httpx.HTTPStatusError as e:
            logger.error("Error fetching events for %s: %s", username, e)
            break

    return events


async def fetch_repo_metadata(owner: str, repo: str) -> dict[str, Any]:
    """Fetch metadata (topics, languages) and top-level file signals for a repo."""
    metadata = {
        "topics": [],
        "language": None,
        "files": [],
        "description": None,
    }

    try:
        repo_resp = await github_client.get(f"/repos/{owner}/{repo}")
        repo_data = repo_resp.json()

        metadata["topics"] = repo_data.get("topics", [])
        metadata["language"] = repo_data.get("language")
        metadata["description"] = repo_data.get("description")

        contents_resp = await github_client.get(f"/repos/{owner}/{repo}/contents")
        contents_data = contents_resp.json()

        if isinstance(contents_data, list):
            metadata["files"] = [
                item["name"] for item in contents_data if item.get("type") in ("file", "dir")
            ]
    except httpx.HTTPStatusError as e:
        logger.warning("Error fetching metadata for %s/%s: %s", owner, repo, e)

    return metadata
