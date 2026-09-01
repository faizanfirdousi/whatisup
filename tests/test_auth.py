import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_me_requires_cookie():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_digest_requires_cookie():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/me/digest")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_digest_v2_requires_cookie():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/me/digest/v2")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sync_following_requires_cookie():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/me/sync-following")
    assert response.status_code == 401
