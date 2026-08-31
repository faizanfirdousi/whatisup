import httpx
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class GitHubRateLimitError(Exception):
    pass


class GitHubClient:
    """Rate-limit-aware httpx wrapper for GitHub API."""

    def __init__(self):
        settings = get_settings()
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {settings.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.base_url = "https://api.github.com"
        # We use a single shared client per instance to pool connections
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.headers, base_url=self.base_url, timeout=10.0
            )
        return self._client

    async def close(self):
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def get(self, endpoint: str, params: dict | None = None) -> httpx.Response:
        """Make a GET request to GitHub, respecting rate limits."""
        client = self.client
        response = await client.get(endpoint, params=params)

        self._check_rate_limit(response)

        # Handle simple rate limiting here. A real app might queue tasks instead of sleeping.
        if response.status_code in (403, 429) and "x-ratelimit-remaining" in response.headers:
            remaining = int(response.headers.get("x-ratelimit-remaining", 1))
            if remaining == 0:
                reset_time = int(response.headers.get("x-ratelimit-reset", 0))
                import time
                sleep_time = max(0, reset_time - int(time.time())) + 1
                logger.warning(f"GitHub Rate Limit Exceeded. Sleeping for {sleep_time}s.")
                # We raise instead of sleep here to let the caller or scheduler handle it,
                # as sleeping for potentially an hour in a web request is bad.
                raise GitHubRateLimitError(f"Rate limit exceeded. Resets in {sleep_time}s.")

        response.raise_for_status()
        return response
        
    def _check_rate_limit(self, response: httpx.Response):
        remaining = response.headers.get("x-ratelimit-remaining")
        if remaining and int(remaining) < 100:
            logger.warning(f"GitHub rate limit running low: {remaining} remaining.")

# Global singleton client
github_client = GitHubClient()
