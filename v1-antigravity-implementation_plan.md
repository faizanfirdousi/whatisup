# WhatIsUp v1 — Execution Plan

## Understanding

**WhatIsUp** is a personal intelligence layer for developer networks. It tracks GitHub activity for people you follow, scores events for significance, extracts technologies, and generates weekly narratives via LLM (OpenRouter).

**v0 today**: Single-PAT, no auth, admin-secret-gated dashboard. APScheduler runs inside uvicorn. Owner is picked from localStorage. All API routes use `owner_id` in the URL with no access control.

**v1 goal**: GitHub OAuth login, per-user token, external cron, two new product surfaces ("Since you last looked" + "Story of your network"), Docker hosting.

## Execution Order — 7 Phases

I'll implement all 7 phases in order, each with backend → migration → frontend → tests.

---

### Phase 0 — External Scheduler (unblocks hosting)

**Backend changes:**
- [MODIFY] `app/main.py` — Remove `start_scheduler`/`stop_scheduler` from lifespan
- [MODIFY] `app/config.py` — Add `cron_secret` setting
- [NEW] `app/models/pipeline_run.py` — `pipeline_runs` table model
- [NEW] `app/routers/internal.py` — `POST /internal/run-pipeline` with `X-Cron-Secret` header auth, phase parameter, advisory lock
- [MODIFY] `app/pipeline.py` — Split into `run_collect` and `run_narrate`, add pipeline_run logging
- [MODIFY] `app/models/__init__.py` — Register PipelineRun
- [MODIFY] `alembic/env.py` — Register PipelineRun
- [NEW] Alembic migration for `pipeline_runs` table
- Keep `app/scheduler.py` as a stub (don't delete file, just empty functions)

---

### Phase 1 — GitHub OAuth + Owner-Scoped API

**Backend changes:**
- [MODIFY] `app/config.py` — Add `github_client_id`, `github_client_secret`, `session_secret`, `token_encryption_key`, `public_app_url`, `frontend_origin`
- [NEW] `app/auth/__init__.py`
- [NEW] `app/auth/github.py` — OAuth authorize + callback, encrypt/store token, upsert Owner by github_id
- [NEW] `app/auth/session.py` — Signed cookie session, `get_current_owner` FastAPI dependency
- [NEW] `app/routers/auth.py` — `/auth/github`, `/auth/github/callback`, `POST /auth/logout`, `GET /api/me`
- [MODIFY] `app/models/owner.py` — Add `github_id`, `encrypted_access_token`, `token_scopes`, `last_login_at`, `person_id`, `is_builder` columns
- [MODIFY] `app/github/client.py` — Support per-token `GitHubClient(token=...)` constructor
- [MODIFY] `app/pipeline.py` — Collect using best available owner token
- [MODIFY] `app/routers/dashboard.py` — All `/api/owners/{id}/...` become `/api/me/...` or require auth. Remove list-all-owners for normal users
- [MODIFY] `app/main.py` — CORS origins from settings, include auth router, add SessionMiddleware
- [NEW] Alembic migration for owners columns + person_id FK
- **Frontend:**
  - [NEW] `frontend/src/pages/Login.jsx`
  - [NEW] `frontend/src/hooks/useAuth.js` — Auth context, `/api/me` check
  - [MODIFY] `frontend/src/api/client.js` — `credentials: 'include'`, drop admin secret from dashboard calls, add new `/api/me/*` methods
  - [MODIFY] `frontend/src/App.jsx` — Auth gate, `/login` route, wrap in AuthProvider
  - [DELETE] `frontend/src/hooks/useSelectedOwner.js` (logic replaced by auth)
  - [DELETE] `frontend/src/hooks/ownerStorage.js` (no more localStorage owner)
  - [DELETE] `frontend/src/components/OwnerSelect.jsx`
  - [MODIFY] `frontend/src/components/Sidebar.jsx` — Avatar + logout, conditional admin
  - [MODIFY] `frontend/src/pages/Dashboard.jsx` — Use `/api/me/digest` instead of owner picker
  - [MODIFY] `frontend/src/pages/Network.jsx` — Use `/api/me/connections`, remove admin secret
  - [MODIFY] `frontend/src/pages/PersonDetail.jsx` — Auth-gated person access
  - [MODIFY] `frontend/vite.config.js` — Proxy `/auth` to backend

---

### Phase 2 — Collector Hardening

**Backend changes:**
- [MODIFY] `app/models/person.py` — Add `events_etag` column
- [MODIFY] `app/github/client.py` — Add `If-None-Match` support, 304 handling
- [MODIFY] `app/github/collector.py` — Use ETags, paginate until empty/304/10 pages, rate limit handling per owner
- [MODIFY] `app/pipeline.py` — Collect per active owner, debounce, rate limit recording
- [NEW] Alembic migration for `people.events_etag`

---

### Phase 3 — Since You Last Looked

**Backend changes:**
- [MODIFY] `app/models/owner.py` — Add `highlights_acked_at`, `last_collected_at`, `collect_in_progress_at` (may be combined with Phase 1 migration)
- [NEW] `app/scoring/since.py` — Ranking + template headlines
- [NEW] `app/routers/me.py` — `GET /api/me/since`, `GET /api/me/highlights`, `POST /api/me/ack`, `POST /api/me/collect`
- [NEW] Alembic migration (if not already in Phase 1)
- **Frontend:**
  - [NEW] `frontend/src/components/SinceLastLooked.jsx`
  - [MODIFY] `frontend/src/pages/Dashboard.jsx` — Lead with "3 things" block, ack on leave/dwell

---

### Phase 4 — Story of Your Network

**Backend changes:**
- [NEW] `app/models/network_story.py` — `network_story_facts` table
- [NEW] `app/network/__init__.py`
- [NEW] `app/network/facts.py` — Pure functions + SQL assembly for rising/declining/new/quiet
- [NEW] `app/network/thresholds.py` — Configurable constants
- [NEW] `app/narrative/network_story.py` — Template + LLM + grounding validation
- [MODIFY] `app/pipeline.py` — `run_narrate` generates stories per active owner
- [NEW] `GET /api/me/network-story` endpoint
- [NEW] Alembic migration for `network_story_facts`
- **Frontend:**
  - [NEW] `frontend/src/components/NetworkStory.jsx`
  - [MODIFY] `frontend/src/pages/Dashboard.jsx` — Network story section above person cards
  - [MODIFY] `frontend/src/pages/Network.jsx` — `?tech=` filter from story bullets

---

### Phase 5 — Highlights API (Extension Contract)

**Backend changes:**
- Verify `GET /api/me/highlights` works correctly (mostly done in Phase 3)
- CORS: add extension origin config
- Document the contract

---

### Phase 6 — Hosting (Docker on VM)

- [MODIFY] `docker-compose.yml` — Full stack: API + DB
- [NEW] `Dockerfile` — Python 3.11-slim API container
- [MODIFY] `.env.example` — All v1 settings
- Systemd timer scripts (documentation)

---

### Phase 7 — Polish

- Hide/gate admin behind `is_builder`
- Error pages (rate limited, empty network, first run)
- Stats: network-level scoping
- README update

---

## Open Questions

> [!IMPORTANT]
> 1. **GitHub OAuth App**: Have you already created a GitHub OAuth App? I need `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` to test the flow locally. The callback URL should be `http://localhost:8000/auth/github/callback`.
> 2. **Token encryption**: Should I generate a `TOKEN_ENCRYPTION_KEY` for Fernet, or do you have one?
> 3. **Session secret**: Any preference for `SESSION_SECRET`, or shall I generate a random one for `.env.example`?

## Verification Plan

### Automated Tests
```bash
pytest tests/ -v
```
New tests: `test_since.py`, `test_network_facts.py`, `test_network_story_validation.py`, `test_pipeline_lock.py`, `test_auth.py`

### Manual (local)
1. Login with GitHub; following list matches GitHub
2. Cannot access another owner's data
3. Trigger collect; second trigger mostly 304s
4. "Since last looked" shows correct items; GET doesn't clear; POST ack does
5. Network story shows correct bullets from structured facts
6. Template fallback works without OpenRouter
