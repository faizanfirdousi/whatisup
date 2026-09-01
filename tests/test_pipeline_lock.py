import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import get_settings

@pytest.fixture(autouse=True)
def _setup_settings():
    settings = get_settings()
    settings.cron_secret = "test-secret"
    yield
    settings.cron_secret = ""

@pytest.mark.asyncio
async def test_cron_secret_required():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/internal/run-pipeline")
    assert response.status_code == 401
    assert "Missing X-Cron-Secret header" in response.text

@pytest.mark.asyncio
async def test_invalid_cron_secret():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/internal/run-pipeline", headers={"X-Cron-Secret": "wrong"})
    assert response.status_code == 401
    assert "Invalid cron secret" in response.text

