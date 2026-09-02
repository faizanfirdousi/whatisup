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


@pytest.mark.asyncio
async def test_repo_metadata_fetches_repo_and_contents_together():
    paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("/contents"):
            return httpx.Response(200, json=[{"name": "go.mod", "type": "file"}])
        return httpx.Response(200, json={"language": "Go", "topics": ["cli"], "description": "x"})

    client = GitHubClient(token="test-token")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.github.com")
    try:
        from app.github.collector import fetch_repo_metadata

        meta = await fetch_repo_metadata(client, "octo", "repo")
    finally:
        await client.close()

    assert "/repos/octo/repo" in paths
    assert "/repos/octo/repo/contents" in paths
    assert meta["language"] == "Go"
    assert "go.mod" in meta["files"]

