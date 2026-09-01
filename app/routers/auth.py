import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.crypto import encrypt_token
from app.auth.github import authorize_url
from app.auth.session import SESSION_COOKIE, SESSION_MAX_AGE, dump_session
from app.config import get_settings
from app.db import get_db
from app.github.client import GitHubClient
from app.models.owner import Owner
from app.pipeline import seed_connections_for_owner

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


@router.get("/auth/github")
async def github_login():
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(status_code=500, detail="GitHub Client ID not configured")
    return RedirectResponse(authorize_url())


@router.get("/auth/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": f"{settings.public_app_url.rstrip('/')}/auth/github/callback",
            },
        )
        data = resp.json()

    if "error" in data:
        logger.error("GitHub OAuth error: %s", data)
        raise HTTPException(status_code=400, detail=data.get("error_description", "OAuth failed"))

    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="OAuth failed: no access token")
    scope = data.get("scope", "")

    gh = GitHubClient(token=access_token)
    try:
        user_resp = await gh.get("/user")
        user_data = user_resp.json()
    finally:
        await gh.close()

    github_id = user_data["id"]
    login = user_data["login"]
    now = datetime.now(timezone.utc)
    encrypted_token = encrypt_token(access_token)

    result = await db.execute(select(Owner).where(Owner.github_id == github_id))
    owner = result.scalar_one_or_none()
    first_login = owner is None

    if owner:
        owner.github_username = login
        owner.label = owner.label or login
        owner.encrypted_access_token = encrypted_token
        owner.token_scopes = scope
        owner.last_login_at = now
    else:
        owner = Owner(
            label=login,
            github_id=github_id,
            github_username=login,
            encrypted_access_token=encrypted_token,
            token_scopes=scope,
            last_login_at=now,
            is_builder=False,
        )
        db.add(owner)
        await db.flush()

    if first_login or not owner.person_id:
        try:
            client = GitHubClient(token=access_token)
            try:
                await seed_connections_for_owner(db, owner.id, login, client=client)
            finally:
                await client.close()
        except Exception:
            logger.exception("Failed to seed following for %s", login)

    await db.commit()

    response = RedirectResponse(url=settings.frontend_origin)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=dump_session(owner.id),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=SESSION_MAX_AGE,
        path="/",
    )
    return response


@router.post("/auth/logout")
async def logout():
    settings = get_settings()
    response = Response(status_code=204)
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        samesite="lax",
        secure=settings.cookie_secure,
        httponly=True,
    )
    return response
