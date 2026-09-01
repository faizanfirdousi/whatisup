from fastapi import Depends, HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models.owner import Owner

# Re-export so existing imports keep working
from app.auth.crypto import decrypt_token, encrypt_token  # noqa: F401

SESSION_COOKIE = "whatisup_session"
SESSION_MAX_AGE = 86400 * 30


def get_session_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret)


def dump_session(owner_id: int) -> str:
    return get_session_serializer().dumps({"owner_id": owner_id})


async def get_current_owner(request: Request, db: AsyncSession = Depends(get_db)) -> Owner:
    session_cookie = request.cookies.get(SESSION_COOKIE)
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        data = get_session_serializer().loads(session_cookie, max_age=SESSION_MAX_AGE)
        owner_id = data.get("owner_id")
        if not owner_id:
            raise HTTPException(status_code=401, detail="Invalid session data")
    except (BadSignature, SignatureExpired, Exception):
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    owner = await db.get(Owner, owner_id)
    if not owner or not owner.is_active:
        raise HTTPException(status_code=401, detail="User account disabled or not found")
    return owner


async def require_builder(owner: Owner = Depends(get_current_owner)) -> Owner:
    if not owner.is_builder:
        raise HTTPException(status_code=403, detail="Builder only")
    return owner
