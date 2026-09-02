import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.rate_limit import limiter
from app.routers import admin, auth, dashboard, health, internal, me, digest_v2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("WhatIsUp starting up...")
    yield
    print("WhatIsUp shutting down...")


app = FastAPI(
    title="WhatIsUp",
    description="A personal intelligence layer for your developer network",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

settings = get_settings()
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://whatisupp.vercel.app",
    settings.frontend_origin,
]
if settings.chrome_extension_origin:
    origins.append(settings.chrome_extension_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in origins if o],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Accept", "X-Admin-Secret", "X-Cron-Secret"],
)

app.include_router(health.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(internal.router)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(digest_v2.router)
