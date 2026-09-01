import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import httpx

from app.db import get_db
from app.config import get_settings
from app.models.owner import Owner
from app.models.connection import Connection
from app.pipeline import seed_connections_for_owner, run_global_pipeline
from app.github.client import GitHubClient
from app.serializers import owner_to_dict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_secret(x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret")):
    expected = (get_settings().admin_secret or "").strip()
    provided = (x_admin_secret or "").strip()
    if provided.startswith("ADMIN_SECRET="):
        provided = provided.split("=", 1)[1].strip()
    if not provided:
        raise HTTPException(
            status_code=401,
            detail="Missing admin secret. Paste the ADMIN_SECRET value from .env.",
        )
    if provided != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin secret. Use the exact ADMIN_SECRET value from .env (not the GitHub or OpenRouter key).",
        )
    return True


class OwnerCreate(BaseModel):
    label: str
    github_username: str
    delivery_email: str | None = None


@router.post("/owners", dependencies=[Depends(verify_admin_secret)])
async def create_owner(owner_in: OwnerCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Owner).where(Owner.github_username == owner_in.github_username)
    )
    owner = result.scalar_one_or_none()
    created = False
    if not owner:
        owner = Owner(
            label=owner_in.label,
            github_username=owner_in.github_username,
            delivery_email=owner_in.delivery_email,
        )
        db.add(owner)
        await db.flush()
        created = True
    else:
        owner.label = owner_in.label
        if owner_in.delivery_email is not None:
            owner.delivery_email = owner_in.delivery_email

    try:
        client = GitHubClient()
        try:
            seed_info = await seed_connections_for_owner(db, owner.id, owner.github_username, client=client)
        finally:
            await client.close()
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else 502
        if status == 404:
            raise HTTPException(status_code=400, detail=f"GitHub user '{owner_in.github_username}' not found")
        if status in (401, 403):
            raise HTTPException(status_code=502, detail="GitHub rejected the request — check GITHUB_TOKEN")
        logger.exception("GitHub error while seeding owner")
        raise HTTPException(status_code=502, detail=f"GitHub API error ({status})")

    return {
        "status": "success",
        "created": created,
        "owner": owner_to_dict(owner),
        "seed": seed_info,
    }


class ConnectionUpdate(BaseModel):
    is_close: bool


@router.patch("/connections/{connection_id}", dependencies=[Depends(verify_admin_secret)])
async def update_connection(
    connection_id: int, update: ConnectionUpdate, db: AsyncSession = Depends(get_db)
):
    conn = await db.get(Connection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    conn.is_close = update.is_close
    return {"status": "success", "connection_id": conn.id, "is_close": conn.is_close}


@router.post("/run-pipeline", dependencies=[Depends(verify_admin_secret)])
async def trigger_pipeline(db: AsyncSession = Depends(get_db)):
    processed = await run_global_pipeline(db)
    return {"status": "success", "people_processed": processed}
