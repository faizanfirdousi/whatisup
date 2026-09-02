import asyncio
import logging
from typing import Any

import httpx

from app.config import get_settings
from app.github.client import GitHubClient

logger = logging.getLogger(__name__)


async def fetch_user(client: GitHubClient, username: str) -> dict[str, Any]:
    """Fetch a GitHub user profile. Raises if the user does not exist."""
    response = await client.get(f"/users/{username}")
    return response.json()


async def fetch_authenticated_following(client: GitHubClient) -> list[dict[str, Any]]:
    """Following list for the authenticated user (`GET /user/following`)."""
    following: list[dict[str, Any]] = []
    page = 1
    while True:
        response = await client.get("/user/following", params={"per_page": 100, "page": page})
        data = response.json()
        if not data:
            break
        following.extend(data)
        if 'rel="next"' not in response.headers.get("link", ""):
            break
        page += 1
    return following


async def fetch_following(client: GitHubClient, username: str) -> list[dict[str, Any]]:
    """Fetch all users a given GitHub user is following (handles pagination)."""
    following: list[dict[str, Any]] = []
    page = 1

    while True:
        response = await client.get(
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


async def fetch_public_events(
    client: GitHubClient, username: str, pages: int | None = None, etag: str | None = None
) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch public events until empty, 304, or `pages` (GitHub caps ~300 events / 90 days)."""
    pages = pages if pages is not None else max(1, get_settings().collect_event_pages)
    events: list[dict[str, Any]] = []
    new_etag = etag

    for page in range(1, pages + 1):
        try:
            # We only use the ETag for the first page to check if there are any new events at all.
            # If there are, we fetch subsequent pages without ETag to get the full history.
            req_etag = etag if page == 1 else None
            response = await client.get(
                f"/users/{username}/events/public",
                params={"per_page": 100, "page": page},
                etag=req_etag,
            )
            
            if response.status_code == 304:
                # 304 Not Modified -> No new events since last check
                logger.info(f"No new events for {username} (304 Not Modified)")
                return [], etag
                
            if page == 1:
                # Save the new ETag from the first page
                new_etag = response.headers.get("etag")

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

    return events, new_etag


async def fetch_repo_metadata(client: GitHubClient, owner: str, repo: str) -> dict[str, Any]:
    """Fetch metadata (topics, languages) and top-level file signals for a repo."""
    metadata = {
        "topics": [],
        "language": None,
        "files": [],
        "description": None,
    }

    try:
        repo_resp, contents_resp = await asyncio.gather(
            client.get(f"/repos/{owner}/{repo}"),
            client.get(f"/repos/{owner}/{repo}/contents"),
            return_exceptions=True,
        )

        if isinstance(repo_resp, Exception):
            raise repo_resp
        repo_data = repo_resp.json()
        metadata["topics"] = repo_data.get("topics", [])
        metadata["language"] = repo_data.get("language")
        metadata["description"] = repo_data.get("description")

        if not isinstance(contents_resp, Exception):
            contents_data = contents_resp.json()
            if isinstance(contents_data, list):
                metadata["files"] = [
                    item["name"] for item in contents_data if item.get("type") in ("file", "dir")
                ]
    except httpx.HTTPStatusError as e:
        logger.warning("Error fetching metadata for %s/%s: %s", owner, repo, e)

    return metadata

