from urllib.parse import urlencode

from app.config import get_settings

GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
OAUTH_SCOPES = "read:user user:follow"


def oauth_callback_url() -> str:
    return f"{get_settings().public_app_url.rstrip('/')}/auth/github/callback"


def authorize_url() -> str:
    settings = get_settings()
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": oauth_callback_url(),
            "scope": OAUTH_SCOPES,
        }
    )
    return f"{GITHUB_AUTHORIZE}?{query}"
