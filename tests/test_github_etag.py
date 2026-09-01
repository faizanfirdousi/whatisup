import httpx
import pytest

from app.github.client import GitHubClient
from app.github.collector import fetch_public_events


@pytest.mark.asyncio
async def test_etag_if_none_match_and_304_skips_body():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["if-none-match"] = request.headers.get("if-none-match")
        return httpx.Response(304, headers={"etag": '"abc"'})

    client = GitHubClient(token="test-token")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.github.com")
    try:
        events, etag = await fetch_public_events(client, "octocat", etag='"abc"')
    finally:
        await client.close()

    assert seen["if-none-match"] == '"abc"'
    assert events == []
    assert etag == '"abc"'
