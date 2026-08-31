# WhatIsUp v0 — Implementation Plan (Final)

Build a developer-network intelligence tool that tracks public GitHub activity of people you follow, scores significance, generates LLM-powered weekly narratives, and displays everything on a **React web dashboard**.

## Key Decisions

| Topic | Decision |
|---|---|
| **LLM** | **OpenRouter free tier** — `meta-llama/llama-3.3-70b-instruct:free` as primary (best free model for structured JSON), `openrouter/free` as fallback router. **Completely free, no payment needed.** Rate limit: 20 req/min, 50 req/day (enough for 50 people weekly). |
| **Frontend** | React via Vite (replaces email delivery) |
| **Database** | Local Docker Postgres |
| **Email** | Skipped entirely for this phase |
| **GitHub Token** | User has it ready ✅ |
| **Python** | 3.11+ ✅ |

> [!NOTE]
> **OpenRouter setup:** Sign up at [openrouter.ai](https://openrouter.ai), go to Keys → Create Key. That's it — no credit card needed. The `:free` suffix models cost $0. You'll put the key in `.env` as `OPENROUTER_API_KEY`.

---

## Proposed Changes

### Phase 0 — Scaffolding (Backend + Frontend)

#### [NEW] [`pyproject.toml`](file:///home/faizan/projects/whatisup/pyproject.toml)
- Dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `httpx`, `apscheduler`, `pydantic-settings`, `python-dotenv`
- Dev: `pytest`, `pytest-asyncio`, `ruff`
- **No `anthropic` SDK** — we use OpenRouter's OpenAI-compatible API via `httpx` directly

#### [NEW] [`docker-compose.yml`](file:///home/faizan/projects/whatisup/docker-compose.yml)
- Postgres 16 container, port 5432, volume persistence

#### [NEW] [`.env.example`](file:///home/faizan/projects/whatisup/.env.example)
```
DATABASE_URL=postgresql+asyncpg://whatisup:whatisup@localhost:5432/whatisup
GITHUB_TOKEN=ghp_...
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
ADMIN_SECRET=change-me-to-something-random
```

#### [NEW] [`app/main.py`](file:///home/faizan/projects/whatisup/app/main.py)
- FastAPI app with lifespan, CORS for React dev server (:5173), router registration

#### [NEW] [`app/config.py`](file:///home/faizan/projects/whatisup/app/config.py) — pydantic-settings
#### [NEW] [`app/db.py`](file:///home/faizan/projects/whatisup/app/db.py) — async SQLAlchemy engine + sessions
#### [NEW] [`app/routers/health.py`](file:///home/faizan/projects/whatisup/app/routers/health.py) — `GET /health`

#### [NEW] [`frontend/`](file:///home/faizan/projects/whatisup/frontend/) — Vite + React project
- `react-router-dom` for routing, dark theme CSS design system

---

### Phase 1 — Data Models & Migrations

#### [NEW] `app/models/` — All 7 tables from PRD Section 8
- `owner.py`, `person.py`, `connection.py`, `activity_event.py`, `technology.py`, `insight.py`, `digest_delivery.py`

#### [NEW] `alembic/` + `alembic.ini` — Initial migration creating all tables

---

### Phase 2 — GitHub Collector

#### [NEW] `app/github/client.py` — Rate-limit-aware httpx wrapper
#### [NEW] `app/github/collector.py` — `fetch_following`, `fetch_public_events`, `fetch_repo_metadata`

---

### Phase 3 — Normalization

#### [NEW] `app/github/normalize.py` — Event type mapping per Section 9.2, idempotent upserts
#### [NEW] `tests/test_normalize.py`

---

### Phase 4 — Significance Scoring

#### [NEW] `app/scoring/significance.py` — Pure function per Section 9.3
#### [NEW] `tests/test_significance.py` — Tests from Appendix A

---

### Phase 5 — Technology Extraction

#### [NEW] `app/scoring/technology.py` — Rule table per Section 9.4

---

### Phase 6 — Weekly Narrative Generation

#### [NEW] `app/narrative/schema.py` — `WeeklyNarrative` Pydantic model
#### [NEW] `app/narrative/prompts.py` — System prompt
#### [NEW] `app/narrative/generate.py`
- Calls OpenRouter API (OpenAI-compatible: `POST https://openrouter.ai/api/v1/chat/completions`)
- Uses `meta-llama/llama-3.3-70b-instruct:free` (falls back to `openrouter/free`)
- Mandatory grounding validation + fallback to template
#### [NEW] `tests/test_narrative_validation.py`

---

### Phase 7 — API Endpoints (Backend for Frontend)

#### [NEW] `app/routers/admin.py`
| Endpoint | Purpose |
|---|---|
| `POST /admin/owners` | Create owner, auto-seed connections from GitHub `/following` |
| `PATCH /admin/connections/{id}` | Toggle `is_close` |
| `POST /admin/run-pipeline` | Manually trigger collect → score → narrate |

#### [NEW] `app/routers/dashboard.py`
| Endpoint | Purpose |
|---|---|
| `GET /api/owners` | List all owners |
| `GET /api/owners/{id}/digest` | Assembled digest (close circle + highlights) |
| `GET /api/owners/{id}/connections` | All connections with person details |
| `GET /api/people/{id}` | Person detail + tech + latest insight |
| `GET /api/people/{id}/events` | Paginated activity events |
| `GET /api/stats` | Overview stats |

#### [NEW] `scripts/add_owner.py` + `scripts/run_pipeline.py`

---

### Phase 8 — React Frontend Dashboard

```
frontend/src/
├── main.jsx / App.jsx          # Router setup
├── index.css                    # Dark theme design system
├── api/client.js                # Backend API wrapper
├── components/
│   ├── Layout.jsx               # Sidebar + content shell
│   ├── Sidebar.jsx              # Navigation
│   ├── PersonCard.jsx           # Avatar, name, tech tags, score
│   ├── InsightCard.jsx          # Narrative display
│   ├── EventTimeline.jsx        # Activity timeline
│   ├── TechBadge.jsx            # Technology pill
│   ├── StatsBar.jsx             # Overview stats
│   └── Loader.jsx               # Loading/skeleton states
├── pages/
│   ├── Dashboard.jsx            # Main: close circle + network highlights
│   ├── Network.jsx              # All connections grid
│   ├── PersonDetail.jsx         # Deep dive per person
│   └── Admin.jsx                # Add owner, run pipeline, manage connections
└── hooks/useApi.js              # Fetch hook with loading/error
```

**Design:** Dark theme, glassmorphism cards, gradient accents, Inter font, micro-animations on hover, responsive layout.

---

### Phase 9 — Scheduling

#### [NEW] `app/scheduler.py`
- APScheduler: daily collection, weekly narrative generation
- Configurable intervals via env vars

---

## Verification Plan

### Automated Tests
```bash
pytest tests/ -v
```

### Manual Verification
- Phase 0: Both servers start (FastAPI :8000, React :5173), `/health` returns 200
- Phase 1: All 7 tables in Postgres
- Phase 2: Real GitHub data fetched for a username
- Phase 3: No duplicates on re-run
- Phase 7: API endpoints return correct data
- Phase 8: Dashboard renders with real data
