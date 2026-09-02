import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models.auth_session import AuthSession
from app.models.owner import Owner

# Re-export so existing imports keep working
from app.auth.crypto import decrypt_token, encrypt_token  # noqa: F401

SESSION_COOKIE = "whatisup_session"
OAUTH_STATE_COOKIE = "whatisup_oauth_state"
SESSION_MAX_AGE = 86400 * 7
OAUTH_STATE_MAX_AGE = 600


def get_session_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret)


def dump_oauth_state(state: str) -> str:
    return get_session_serializer().dumps({"s": state})


def load_oauth_state(cookie: str) -> str | None:
    try:
        data = get_session_serializer().loads(cookie, max_age=OAUTH_STATE_MAX_AGE)
        value = data.get("s")
        return value if isinstance(value, str) and value else None
    except (BadSignature, SignatureExpired, Exception):
        return None


def _cookie_kwargs() -> dict:
    settings = get_settings()
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.cookie_secure,
        "path": "/",
    }


def apply_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE,
        **_cookie_kwargs(),
    )


def apply_oauth_state_cookie(response: Response, state: str) -> None:
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=dump_oauth_state(state),
        max_age=OAUTH_STATE_MAX_AGE,
        **_cookie_kwargs(),
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, **_cookie_kwargs())


def clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(key=OAUTH_STATE_COOKIE, **_cookie_kwargs())


def _sign_session_id(session_id: str) -> str:
    return get_session_serializer().dumps({"sid": session_id})


def _unsigned_session_id(session_cookie: str) -> str | None:
    try:
        data = get_session_serializer().loads(session_cookie, max_age=SESSION_MAX_AGE)
        sid = data.get("sid")
        return sid if isinstance(sid, str) and sid else None
    except (BadSignature, SignatureExpired, Exception):
        return None


async def create_session(db: AsyncSession, owner_id: int) -> str:
    now = datetime.now(timezone.utc)
    session_id = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            id=session_id,
            owner_id=owner_id,
            expires_at=now + timedelta(seconds=SESSION_MAX_AGE),
            last_seen_at=now,
        )
    )
    await db.flush()
    return _sign_session_id(session_id)


async def revoke_session_cookie(db: AsyncSession, session_cookie: str | None) -> None:
    if not session_cookie:
        return
    sid = _unsigned_session_id(session_cookie)
    if not sid:
        return
    row = await db.get(AuthSession, sid)
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)


async def get_current_owner(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Owner:
    session_cookie = request.cookies.get(SESSION_COOKIE)
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sid = _unsigned_session_id(session_cookie)
    if not sid:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    row = await db.get(AuthSession, sid)
    now = datetime.now(timezone.utc)
    if (
        not row
        or row.revoked_at is not None
        or row.expires_at <= now
    ):
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    owner = await db.get(Owner, row.owner_id)
    if not owner or not owner.is_active:
        raise HTTPException(status_code=401, detail="User account disabled or not found")

    last_seen = row.last_seen_at
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    should_touch = last_seen is None or (now - last_seen).total_seconds() > 3600
    if should_touch:
        row.last_seen_at = now
        row.expires_at = now + timedelta(seconds=SESSION_MAX_AGE)
        apply_session_cookie(response, _sign_session_id(row.id))
    return owner


async def require_builder(owner: Owner = Depends(get_current_owner)) -> Owner:
    if not owner.is_builder:
        raise HTTPException(status_code=403, detail="Builder only")
    return owner
