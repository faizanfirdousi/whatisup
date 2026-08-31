from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic liveness check — unauthenticated."""
    return {"status": "ok", "service": "whatisup"}
