import hmac
import logging
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.crypto import decrypt_token, encrypt_token
from app.auth.github import authorize_url
from app.auth.session import (
    SESSION_COOKIE,
    apply_oauth_state_cookie,
    apply_session_cookie,
    clear_oauth_state_cookie,
    clear_session_cookie,
    create_session,
    load_oauth_state,
    revoke_session_cookie,
    OAUTH_STATE_COOKIE,
)
from app.config import get_settings
from app.db import async_session, get_db
from app.github.client import GitHubClient
from app.models.owner import Owner
from app.pipeline import run_collect_for_owner, seed_connections_for_owner
from app.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


async def _seed_then_collect(owner_id: int, github_username: str) -> None:
    async with async_session() as session:
        try:
            owner = await session.get(Owner, owner_id)
            if not owner or not owner.encrypted_access_token:
                if owner:
                    owner.collect_in_progress_at = None
                    await session.commit()
                return
            token = decrypt_token(owner.encrypted_access_token)
            client = GitHubClient(token=token)
            try:
                await seed_connections_for_owner(session, owner_id, github_username, client=client)
                await session.commit()
            finally:
                await client.close()
            await run_collect_for_owner(session, owner_id)
            owner = await session.get(Owner, owner_id)
            if owner and owner.collect_in_progress_at is not None:
                owner.collect_in_progress_at = None
                await session.commit()
        except Exception:
            logger.exception("Failed to seed/collect after login for owner %s", owner_id)
            owner = await session.get(Owner, owner_id)
            if owner:
                owner.collect_in_progress_at = None
                await session.commit()


def _oauth_state_valid(query_state: str | None, cookie_state: str | None) -> bool:
    if not query_state or not cookie_state:
        return False
    return hmac.compare_digest(query_state, cookie_state)


@router.get("/auth/github")
@limiter.limit("10/minute")
async def github_login(request: Request):
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(status_code=500, detail="GitHub Client ID not configured")
    state = secrets.token_urlsafe(32)
    response = RedirectResponse(authorize_url(state))
    apply_oauth_state_cookie(response, state)
    return response


@router.get("/auth/github/callback")
@limiter.limit("5/minute")
async def github_callback(
    request: Request,
    code: str,
    background_tasks: BackgroundTasks,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    stored = load_oauth_state(request.cookies.get(OAUTH_STATE_COOKIE) or "")
    if not _oauth_state_valid(state, stored):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

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
        logger.error(
            "GitHub OAuth error: %s - %s",
            data.get("error"),
            data.get("error_description"),
        )
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

    needs_seed = first_login or not owner.person_id
    if needs_seed:
        owner.collect_in_progress_at = now

    session_token = await create_session(db, owner.id)
    await db.commit()
    if needs_seed:
        background_tasks.add_task(_seed_then_collect, owner.id, login)

    response = RedirectResponse(url=settings.frontend_origin)
    apply_session_cookie(response, session_token)
    clear_oauth_state_cookie(response)
    return response


@router.post("/auth/logout")
@limiter.limit("20/minute")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    await revoke_session_cookie(db, request.cookies.get(SESSION_COOKIE))
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response
