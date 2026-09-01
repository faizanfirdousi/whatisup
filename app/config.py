from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://whatisup:whatisup@localhost:5432/whatisup"

    # GitHub PAT (fallback / local dev only in v1)
    github_token: str = ""

    # GitHub OAuth (v1)
    github_client_id: str = ""
    github_client_secret: str = ""

    # OpenRouter LLM
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Admin
    admin_secret: str = "change-me-to-something-random"

    # Cron / internal pipeline trigger (v1)
    cron_secret: str = ""

    # Session (v1)
    session_secret: str = "change-me-session-secret"

    # Token encryption (v1 — Fernet key for GitHub access tokens)
    token_encryption_key: str = ""

    # URLs
    public_app_url: str = "http://localhost:8000"
    frontend_origin: str = "http://localhost:5173"
    chrome_extension_origin: str = ""

    # Cookies (set true behind HTTPS)
    cookie_secure: bool = False

    # Collector tuning
    collect_min_interval: int = 900  # seconds (15 min debounce)

    # App
    app_name: str = "WhatIsUp"
    debug: bool = False

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
