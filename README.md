# WhatIsUp

A personal intelligence layer for your GitHub network. Sign in with GitHub, see what changed since you last looked, and get a grounded story of what your people are building.

## What it does

WhatIsUp watches the developers you follow on GitHub — not a firehose of every commit, but the signal that matters: new repos, releases, deep work streaks, tech shifts, and cross-network patterns. It scores activity for significance, deduplicates noise, and turns the week into readable narratives: per-person insights and a network-level story.

You mark highlights as read when you are caught up; the dashboard stays anchored to *since you last looked*.

## Architecture

```
GitHub OAuth + API
       │
       ▼
  collect pipeline ──► Postgres (people, connections, events, technologies, insights)
       │
       ▼
  narrate pipeline ──► LLM stories (OpenRouter) + template fallbacks
       │
       ▼
  FastAPI (:8000) ◄──► React/Vite SPA (dev :5173, prod Vercel)
```

| Layer | Stack |
|-------|-------|
| API | FastAPI, SQLAlchemy async, Alembic |
| Frontend | React, Vite |
| Data | PostgreSQL |
| Auth | GitHub OAuth, encrypted token storage, signed session cookies |
| Intelligence | Significance scoring, tech extraction, network facts, feed selection |
| Narrative | Weekly LLM generation with grounded evidence; template paths when LLM is off |

**Backend layout:** `app/github/` collects and normalizes events; `app/scoring/` ranks significance and extracts technologies; `app/network/` builds facts, clusters, and feed selection; `app/narrative/` generates person insights and network stories; `app/pipeline.py` orchestrates collect and narrate phases.

**Pipeline runs outside the web process** — triggered by cron or a visit with `?refresh=1` (15-minute debounce). The API serves reads and auth; collection and narration are batch jobs.

## Local development

1. Copy `.env.example` to `.env` and fill GitHub OAuth, `SESSION_SECRET`, and a Fernet `TOKEN_ENCRYPTION_KEY`.
2. Create a GitHub OAuth App with callback `http://localhost:8000/auth/github/callback`.
3. Start Postgres and the API:

```bash
docker compose up -d db
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

4. Frontend:

```bash
cd frontend && npm install && npm run dev
```

Vite proxies `/api`, `/auth`, `/admin`, and `/health` to `:8000`. Open `http://localhost:5173`.

Set `is_builder = true` on your `owners` row if you need the Admin page.

## Pipeline

Collection does **not** run inside uvicorn. Trigger it externally:

```bash
curl -X POST "http://localhost:8000/internal/run-pipeline?phase=collect" \
  -H "X-Cron-Secret: $CRON_SECRET"
```

Monday narrate (person insights + network stories):

```bash
curl -X POST "http://localhost:8000/internal/run-pipeline?phase=narrate" \
  -H "X-Cron-Secret: $CRON_SECRET"
```

Visit-triggered collect: `GET /api/me/highlights?refresh=1` (15 minute debounce, does not mark unread as read). Ack with `POST /api/me/ack`.

## Docker (API + Postgres)

```bash
docker compose up -d --build
```

API listens on `:8080`. Point the OAuth callback at `http://localhost:8080/auth/github/callback` if you are not using Vite.

On a VM, add systemd timers that curl loopback with `X-Cron-Secret` (`phase=collect` nightly, `phase=narrate` Mondays). Open 80/443 only; keep Postgres off the public interface.

## Tests

```bash
pytest tests/ -v
```
