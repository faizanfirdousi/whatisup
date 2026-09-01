# WhatIsUp v1 — Implementation Plan (Full)

Turn the local, no-auth, single-PAT dashboard into a **hosted, GitHub-signed-in product**: one owner per login, per-user GitHub rate limits, an external pipeline trigger, and two product surfaces that the v0 feed does not have.

v0 already does: collect public GitHub activity → normalize → score → template-first LLM narrative → per-person digest. v1 does not replace that. It makes it **safe to host**, **scoped to you**, and **about the network, not only the individuals**.

---

## Product thesis for v1

v0 answers: *what did each person I follow do this week?*

v1 answers, in this order:

1. **What changed since I last looked?** (so opening the app has a job)
2. **What is my network doing collectively?** (so the product is a map, not a contact list)
3. Then the existing close-circle + person pages, as drill-down

Those two new surfaces are the only creative features in this plan. Everything else is the platform they require.

---

## Features in scope (and why these two)

| Feature | Why v1, not later |
|---|---|
| **Since you last looked** | Retention and the extension feed. Needs `highlights_acked_at` + visit-triggered collect + existing events. |
| **Story of your network** | Highest-leverage creative feature. Deterministic aggregates over `person_technologies` + events already in Postgres; LLM only narrates grounded facts. Needs owner-scoped reads, which OAuth gives you. |

### Explicitly not in v1

Do not start these in this pass. They need more history, a relevance model, or a second LLM personality we have not grounded yet.

| Deferred | Why wait |
|---|---|
| Developer Journeys / milestones | Needs months of stored events. After 8–12 weeks of pipeline runs, add a `milestones` table derived from first-seen event types and first-seen techs. |
| Why this matters (LLM interpretation layer) | Easy to hallucinate motive. Ship network story with **rule-based "why" templates** first; a second LLM sentence comes in v1.1 if grounding holds. |
| Reconnect / parallel paths / personal context | Need a first-class model of *you* (your own events as a compared series) plus overlap scoring. Personal context is v1.1 once the owner is always a tracked `Person`. |
| Interestingness = significance × relevance × novelty × conversation | Keep **significance** rule-based. Add a tiny **novelty** flag (tech or event type first-seen for that person in our DB) inside "since last visit". Do not split four scores until we have usage. |
| Full Chrome/Firefox extension UI | v1 ships the **highlights API, visit-triggered collect, ack vs refresh split, CORS**. Manifest/content script is a follow-on once the EC2 API is live. |
| GraphQL enrichment, model tiering, owner-scoped person narratives | Quality upgrades. Do not block OAuth/hosting. |

---

## Key decisions

| Topic | Decision |
|---|---|
| **Auth** | Sign in with GitHub OAuth (`read:user`, `user:follow` optional; public-data collection uses the user token). No passwords. |
| **Identity** | `Owner` **is** the logged-in user. `github_username` / `github_id` become verified claims. Seed following on first login. |
| **Sessions** | HTTP-only signed cookie (itsdangerous or Starlette SessionMiddleware + `SESSION_SECRET`). No JWT in `localStorage`. |
| **GitHub API** | Per-owner access token for all collection for that owner's network. Keep `GITHUB_TOKEN` only as a fallback for local/dev and for shared `Person` rows not currently owned (optional; default: skip people with no active owner). |
| **Pipeline trigger** | Delete in-process APScheduler. Nightly/weekly jobs: `POST /internal/run-pipeline` with `X-Cron-Secret` from a **systemd timer or crontab on the VM**. Mid-day freshness: on-demand collect from the dashboard/extension (debounced), not a second in-process scheduler. |
| **Person / Event / Insight** | Stay **global**. Two owners following the same person still share one `people` row and one weekly `insights` row. |
| **New owner-scoped artifacts** | `network_stories` (weekly), separate **ack vs collect** timestamps on `owners`, derived highlights (computed, not stored as a third narrative table). |
| **LLM** | Same pattern: compute structured facts first, then LLM, then validate. OpenRouter stays; network story is **one extra call per owner per week**, not per person. **No LLM on GitHub page views.** |
| **Frontend** | Same Vite React app. Auth gate, new home composition, drop owner-picker / admin-secret-in-localStorage. |
| **Hosting** | **API always-on VM (EC2 by default), Dockerized** so the same image runs locally, on EC2, or any other VPS. SPA → Vercel *or* static files on the same VM. Postgres → Supabase, RDS, or Postgres in Compose on the VM. No Cloud Run / no serverless API. |
| **Admin** | Builder-only: cron secret + optional `ADMIN_SECRET` for `POST /admin/run-pipeline` locally. Public `/api/*` never uses a shared secret. |

---

## Architecture (v1)

```
                    ┌─────────────────────────────────────────┐
                    │  VM (EC2 or any VPS)  docker compose    │
   browser / ext ──►│  FastAPI  :8080                         │
                    │  (optional: Caddy/nginx TLS + SPA)      │
                    └───────────┬─────────────────────────────┘
                                │
                                ├── GET  /api/me/since
                                ├── GET  /api/me/highlights     (refresh; never acks)
                                ├── POST /api/me/ack            (user actually looked)
                                ├── POST /api/me/collect        (debounced GitHub pull)
                                ├── GET  /api/me/network-story
                                └── digest / person / events

systemd timer (VM) ──POST /internal/run-pipeline──► nightly collect+score
                                                 ► Monday narrate (insights + network story)

GitHub homepage visit (extension)
    → GET /api/me/highlights?refresh=1
    → if owner.last_collected_at older than 15 min: enqueue collect (ETag)
    → return current items immediately; extension refetches after ~3s if collecting
```

**Invariant:** the LLM never invents counts, names, or technologies. Every bullet in the network story and every "since last visit" item must cite `person_id`s, `event_id`s, and/or `technology_id`s that exist in the structured payload.

**Two clocks (do not mix these):**

| Clock | Field | Advances when | Does **not** advance when |
|---|---|---|---|
| **Data freshness** | `owners.last_collected_at` | Debounced collect finishes (cron or visit-triggered) | User opening GitHub / dashboard |
| **Seen / unread** | `owners.highlights_acked_at` | User **consumes** the list (dashboard section viewed + ack, popover opened, or click-through) | Loading `github.com`, content-script inject, background alarm, `GET` highlights |

People will open GitHub many times a day. Each visit **refreshes data** (subject to debounce). Unread items **stay** until they actually look at WhatIsUp. Otherwise the badge would clear on the first homepage load and never be useful.

---

## Schema (additive — no rewrite of v0 tables)

Alembic revision on top of `151d9eeeba71`.

### `owners` — columns to add

```text
github_id              BIGINT UNIQUE          -- GitHub numeric id (required after first OAuth)
github_oauth_id        TEXT UNIQUE            -- same as str(github_id); keep if you want a string key
encrypted_access_token TEXT                   -- Fernet(GITHUB_TOKEN_FERNET_KEY)
token_scopes           TEXT
last_login_at          TIMESTAMPTZ
last_collected_at      TIMESTAMPTZ            -- last successful GitHub pull for this owner's network
collect_in_progress_at TIMESTAMPTZ            -- debounce / single-flight collect
highlights_acked_at    TIMESTAMPTZ            -- unread cursor ("since you last looked")
person_id              INTEGER REFERENCES people(id)  -- the owner's own Person row
```

`label` can default to GitHub login. `github_username` stays, now verified.

**Do not** treat "opened github.com" as an ack. Optional `owner_visits` table is only for analytics later; v1 uses the two timestamps above.

### `network_story_facts` (structured, owner-scoped, weekly)

Do **not** store only prose.

```text
id                 SERIAL PK
owner_id           INTEGER NOT NULL REFERENCES owners(id)
week_start         DATE NOT NULL
week_end           DATE NOT NULL
facts              JSONB NOT NULL   -- see schema below
narrative_text     TEXT NOT NULL    -- LLM or template
model_used         TEXT NOT NULL
generated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE (owner_id, week_start)
```

### `facts` JSON shape (computed in Python, no LLM)

```json
{
  "week_start": "2026-09-01",
  "week_end": "2026-09-07",
  "network_size": 42,
  "close_circle_size": 5,
  "active_person_ids": [1, 2, 3],
  "quiet_close_person_ids": [9, 10],
  "tech_this_week": [
    {"name": "kubernetes", "person_ids": [1, 4, 7], "new_to_person_ids": [7]}
  ],
  "tech_prior_window": [
    {"name": "kubernetes", "person_count": 2, "window_days": 28}
  ],
  "rising": [{"name": "kubernetes", "this_week_people": 5, "prior_4w_avg_people": 1.2}],
  "new_in_network": [{"name": "vllm", "person_ids": [12, 15]}],
  "declining": [{"name": "jquery", "this_week_people": 0, "prior_4w_people": 4}],
  "first_external_oss": [{"person_id": 3, "event_id": 881, "repo": "org/repo"}],
  "event_type_counts": {"pull_request_merged": 11, "push": 90}
}
```

**Rising / declining / new** are all SQL over `person_technologies.last_seen_at` and this week's events' repo metadata — not model opinion.

### Optional: `person_tech_first_seen`

If `last_seen_at` alone cannot tell "first time we ever saw Kubernetes on Alice", add:

```text
person_id, technology_id, first_seen_at
```

Backfill: `MIN` from events/metadata where possible; else `last_seen_at` on existing rows (honest: "first *tracked* appearance").

### Token encryption

`cryptography.fernet` with `TOKEN_ENCRYPTION_KEY` in env. Never log tokens. Never send them to the frontend.

---

## Feature 1 — Since you last looked

### Behavior

Unread is keyed off `highlights_acked_at` (null → last 7 days). **GET never writes this field.**

1. Compute at most 3 items with `occurred_at > highlights_acked_at` (plus network-cluster rules).
2. Return them. Dashboard and extension both use this list.
3. Advance `highlights_acked_at` only via `POST /api/me/ack` (see below).

Empty state copy: "Nothing new since {date}. Your network was quiet — or the pipeline has not run yet."

### GitHub homepage / extension: refresh every visit without burning unread

Someone will hit `github.com` (feed, PRs, profile) many times a day. The extension must **update the overlay on every such visit**, but that is a *read + optional collect*, not a *mark as read*.

**Client (content script on `https://github.com/*`, including `/`):**

1. On each page load (and when the tab becomes visible), call `GET /api/me/highlights?refresh=1`.
2. Render badge / nav count from the response immediately.
3. If `collecting: true`, wait ~3s and GET again once (or listen until `collected_at` changes). Do not spin a loop.
4. Opening the **popover** (user looked at the three items) → `POST /api/me/ack`. Clicking through to the dashboard person page → ack that item (or ack all visible). Injecting a badge on the homepage → **no ack**.
5. `chrome.alarms` every 15–30 min is a backup for when they are not on GitHub. Same GET; same no-ack rule.

**Server (`refresh=1`):**

1. Always return highlights from **current Postgres** vs `highlights_acked_at`.
2. If `now - last_collected_at >= COLLECT_MIN_INTERVAL` (default **15 minutes**) and no collect in progress: start `run_collect` **for this owner only** in a background task (or return 202 and let a worker pick it up). Set `collect_in_progress_at`.
3. If they loaded GitHub 12 times in 10 minutes: **one** collect, eleven cheap GETs.
4. Collect uses ETags. Unchanged people cost one 304 each. New events are scored immediately. **Do not** run the weekly LLM / network-story job on this path — templates for new event headlines are enough mid-day.
5. When collect finishes: `last_collected_at = now()`, clear `collect_in_progress_at`. Next GET (or the client's 3s refetch) can show a new item.

**Rate-limit envelope (one owner, 50 people, 15 min floor):** at most four collects/hour ≈ 200 GitHub HTTP calls/hour if every user 304s; still fine vs 5,000/hour. Cron at night remains the full sweep so data is not only "when they opened GitHub."

```
GET  /api/me/highlights?refresh=0|1
     → {
         "since": "<highlights_acked_at>",
         "collected_at": "...",
         "collecting": false,
         "unread_count": 3,
         "items": [ ... ]
       }

POST /api/me/collect          # optional explicit refresh; same debounce as refresh=1
POST /api/me/ack
     body: { "surface": "dashboard" | "extension_popover" | "extension_click",
             "item_ids": ["event:881"] | null }   # null = ack all currently visible
```

`GET /api/me/since` is the dashboard-sized payload (same ranking, richer fields). Same ack cursor. Dashboard should call `POST /api/me/ack` after the "3 things" block has been shown (e.g. on unmount or after a short dwell), **not** on the first paint if you want the extension badge to stay in sync — pick one product rule and use it everywhere:

**v1 rule:** ack = "user opened the WhatIsUp dashboard home or the extension popover." GitHub.com page views never ack.

### Item types (deterministic; LLM optional one-liner later, not in v1)

| Type | Rule | Example |
|---|---|---|
| `high_significance` | Event with `occurred_at > highlights_acked_at` and score ≥ 10, prefer close circle | Sarah merged an external PR |
| `first_external` | `pull_request_opened` / `_merged` + `is_external` and no prior external PR for that person in our DB | First tracked OSS contribution |
| `tech_novelty` | Tech on a person with `first_seen_at > since` | Arjun's first tracked Docker week |
| `network_cluster` | From this week's `network_story_facts`: a rising tech with ≥ 3 people, at least one close | Docker across the close circle |
| `close_quiet` | Close-circle person with zero events since `since` **and** they had events in the prior 14 days | Only include if it would not fill all 3 slots with quietness |

Each item:

```json
{
  "id": "event:881",
  "kind": "first_external",
  "headline": "Sarah merged her first tracked PR to an external repo",
  "reason": "significance 12 · close circle · first external PR in our data",
  "person_id": 44,
  "event_ids": [881],
  "href": "/person/44"
}
```

Headlines are **templates**, not LLM. That keeps this endpoint fast and extension-safe.

### Ranking (v1 "interestingness" lite)

Do not add four score columns. Rank with a single integer:

```
rank = significance_score
     + 20 if is_close
     + 15 if first_external or tech_first_seen
     + 10 if kind == network_cluster
```

That is relevance (close) + novelty (firsts) on top of existing significance. Document it in `app/scoring/since.py` with unit tests.

Frontend: home page **opens with this block**, then network story, then close circle. After dwell or when leaving home, `POST /api/me/ack`.

---

## Feature 2 — Story of your network

### Behavior

Dashboard section **above** person cards:

**Your network this week**

- 7 people worked with Kubernetes-related projects
- 3 people started contributing to open source (first external PR in tracked history)
- Go activity increased vs the prior 4 weeks (12 people this week, 4-week average 5)
- Two people independently showed AI-inference-related topics (`vllm`, `inference`) who had not had those techs before
- Close circle was quiet: 4 of 5 close connections had no events this week

Click a bullet → filtered people list or person page.

A second block when `new_in_network` or `rising` is strong:

**Something interesting is happening**

> Kubernetes appeared in repositories belonging to 5 people you follow this week. Three of those people had never used it in tracked repositories before.

### Computation (no LLM) — `app/network/facts.py`

For `owner_id`, week bounds (reuse `current_week_bounds()`):

1. Person set = `connections` for owner (exclude or include self via `owner.person_id`; **include self in personal-context later, exclude from "people you follow" bullets**).
2. Events this week for those people.
3. Techs this week: from event `metadata` extraction **and/or** `person_technologies` with `last_seen_at` in week (prefer event-linked techs so "worked with Kubernetes this week" is true).
4. Prior window: last 28 days excluding this week, same measures.
5. Rising: `this_week_unique_people >= 3` and `this_week >= 2 * prior_weekly_avg` (tune; test with fixtures).
6. New in network: tech seen this week for ≥ 2 people, `first_seen` this week for those people, **and** not in anyone else's profile before this week.
7. First external OSS: persons whose first `is_external` PR event falls in this week.
8. Close inactive: `is_close` and zero events this week.

All thresholds in `app/network/thresholds.py` so they are testable.

### LLM pass — `app/narrative/network_story.py`

Same contract as person narratives:

1. Always build a **template story** from `facts` (bullet list, no flourish).
2. If OpenRouter is configured, send **only** `facts` (ids and counts, not prior prose).
3. Pydantic:

```python
class NetworkStoryOut(BaseModel):
    headline: str          # one line
    bullets: list[str]     # 3–6 items
    interesting: str | None
    cited_person_ids: list[int]
    cited_techs: list[str]
```

4. Validate: every cited person/tech appears in `facts`; bullet count ≤ 6; no person names that are not in the payload (pass `id → username` map). On failure → template.
5. Store in `network_stories`.

**Prompt rules (keep):** no motives, no "they are pivoting their career", no technologies not in `facts`. "Why this matters" in v1 is **only** the interesting template for rising/new-in-network, e.g. "Three of those people had never used it in tracked repositories before." That sentence is assembled from `new_to_person_ids`, not invented.

### Pipeline hook

After all person insights for an owner's network in a weekly run:

```
await generate_network_story(session, owner_id, facts)
```

Daily collect can skip this (facts would be mid-week noisy). **Weekly job** (Monday) generates stories; daily job is collect+score only. Split `run_global_pipeline` into:

- `run_collect(session)` — events + tech + scores
- `run_narrate(session)` — per-person insight + per-owner network story

Nightly collect on the VM (systemd timer); weekly (Monday) narrate. Mid-day: owner-scoped collect from `?refresh=1` only. `POST /internal/run-pipeline?phase=collect|narrate|all`.

---

## Phases

Do not start a phase until the previous Definition of Done is met.

### Phase 0 — External scheduler (unblocks hosting)

**Why first:** the API will live on a VM, but collection must not live *inside* uvicorn workers (two containers / two workers would double-fire). Cron is `curl` from the host.

| Change | Detail |
|---|---|
| Remove | `start_scheduler` / `stop_scheduler` from `app/main.py` lifespan; delete or stub `app/scheduler.py` |
| Add | `POST /internal/run-pipeline` — header `X-Cron-Secret` matching `CRON_SECRET`. Query `phase=collect\|narrate\|all`. Return 409 if a run is already in progress (see lock below). |
| Add | `POST /api/me/collect` (auth required) — **this owner's** network only, 15 min debounce, no narrate |
| Keep | `POST /admin/run-pipeline` for local use with `ADMIN_SECRET` |
| Lock | `pipeline_runs` table or Postgres advisory lock so cron and a visit-triggered collect cannot stomp each other globally; per-owner `collect_in_progress_at` for the refresh path |

```text
pipeline_runs: id, phase, started_at, finished_at, status, error, people_processed
```

**DoD:** app starts with no APScheduler; curling the internal endpoint runs the pipeline; two overlapping calls do not duplicate work.

**Tests:** lock behavior with a fake session; 401 without cron secret.

---

### Phase 1 — GitHub OAuth + owner-scoped API

| File | Work |
|---|---|
| `app/config.py` | `github_client_id`, `github_client_secret`, `session_secret`, `token_encryption_key`, `public_app_url`, `cron_secret` |
| `app/auth/github.py` | OAuth authorize + callback (`httpx`); encrypt/store token; upsert `Owner` by `github_id` |
| `app/auth/session.py` | Sign cookie `whatisup_session={owner_id}`; `get_current_owner` dependency |
| `app/routers/auth.py` | `GET /auth/github`, `GET /auth/github/callback`, `POST /auth/logout`, `GET /api/me` |
| `app/github/client.py` | Construct client **per token**, not only the global PAT. `GitHubClient(token: str)` |
| `app/pipeline.py` | Collect using the **best available owner token** among owners connected to that person (prefer most recently logged-in). If none, skip or use fallback PAT in debug only |
| `app/routers/dashboard.py` | All `/api/owners/{id}/...` become `/api/me/...` or require `owner.id == current_owner.id`. **List-all-owners goes away** for normal users |
| `app/main.py` | CORS: Vite origin + `FRONTEND_ORIGIN` (Vercel) + later `chrome-extension://<id>` |

On first login:

1. Upsert `Owner`.
2. `get_or_create_person` for the user; set `owner.person_id`.
3. `seed_connections_for_owner` using **their** token (`GET /user/following` is better than `/users/{u}/following` when authenticated as them).
4. Do **not** block the OAuth callback on a full pipeline. Return to the dashboard; first `GET /api/me/highlights?refresh=1` (or `POST /api/me/collect`) starts the owner-scoped collect. Show "collecting your network…" until `collecting` is false.

**Frontend**

- `/login` page: "Continue with GitHub".
- `api/client.js`: `credentials: 'include'`. Drop `X-Admin-Secret` from dashboard calls.
- `useSelectedOwner` / `OwnerSelect` / localStorage owner id: **delete**.
- Layout: avatar + logout. Admin page: only if `owner.is_builder` (new boolean, default false; set in DB for you).

**DoD:** cannot read another owner's digest by guessing `owner_id`. Unauthenticated `/api/me/digest` → 401. Login seeds following.

**Tests:** dependency rejects missing cookie; dashboard queries filter `Connection.owner_id == current`.

---

### Phase 2 — Collector hardening (still REST)

| Change | Detail |
|---|---|
| ETag | Store `people.events_etag`. Send `If-None-Match`; 304 → skip parse. |
| Cap | Keep GitHub's 300-event / 90-day ceiling documented in UI ("based on public activity GitHub exposes"). |
| `per_page` | Events API often returns 30/page regardless; paginate until empty, 304, or 10 pages. Do not assume 100×2. |
| Rate limit | On `GitHubRateLimitError`, stop that owner's batch and continue others; record in `pipeline_runs`. |
| Scope | Nightly `run_collect` iterates **active owners**, then union of their `person_id`s. Visit-triggered collect is **one owner**. |
| Debounce | `COLLECT_MIN_INTERVAL=900` seconds per owner. Ignore overlapping collect if `collect_in_progress_at` is set and younger than 10 minutes (crash recovery: treat older as stale). |

**DoD:** second collect of an unchanged user is mostly 304s; twelve `?refresh=1` calls within 15 minutes start **one** GitHub sweep; pipeline log shows remaining rate limit per owner.

**Tests:** client sets `If-None-Match`; 304 path does not insert events (httpx mock).

---

### Phase 3 — Since you last looked

| File | Work |
|---|---|
| Alembic | `owners.highlights_acked_at`, `last_collected_at`, `collect_in_progress_at` |
| `app/scoring/since.py` | Rank + templates |
| `app/routers/me.py` | `GET /api/me/since`, `GET /api/me/highlights`, `POST /api/me/ack`, `POST /api/me/collect` |
| `frontend/src/pages/Dashboard.jsx` | Lead with "3 things worth knowing"; ack on leave/dwell, not on every poll |
| `frontend/src/components/SinceLastLooked.jsx` | List + links to `/person/:id` |
| `tests/test_since.py` | Ranking: close + first external beats a lone push. GET does not change `highlights_acked_at`. Ack clears items. Refresh debounce: second collect skipped. |

**DoD:** after ack, a second load with no new events shows empty/quiet. A new high-score event after collect appears in the three **without** requiring ack to have been reset by a GitHub page view. Close-circle first-external always outranks a stranger's push.

---

### Phase 4 — Story of your network

| File | Work |
|---|---|
| Alembic | `network_stories`, optional `person_tech_first_seen` |
| `app/network/facts.py` | Pure functions + SQL assembly |
| `app/network/thresholds.py` | Constants |
| `app/narrative/network_story.py` | Template + LLM + grounding |
| `app/pipeline.py` | `run_narrate` generates stories per active owner after person insights |
| `GET /api/me/network-story` | Latest week; 404 → compute-on-read template from facts if narrate has not run (nice for first week) |
| `frontend/src/components/NetworkStory.jsx` | Bullets, rising/new callout, click → `/network?tech=kubernetes` |
| `frontend/src/pages/Network.jsx` | Query filter by tech |
| `tests/test_network_facts.py` | Rising, new-in-network, quiet close circle, first external |
| `tests/test_network_story_validation.py` | Hallucinated tech / unknown person_id → template |

**DoD:** with a fixture network (5 people, planted techs/events), facts JSON matches expected counts **without** calling OpenRouter. LLM path rejects extra names. Dashboard shows the story above person cards.

---

### Phase 5 — Highlights API (extension contract, no store listing yet)

Same ranking as "since last looked". **GET never acks.** `?refresh=1` may start a debounced owner collect (Phase 2/3). CORS: `FRONTEND_ORIGIN` plus later `chrome-extension://<id>`.

Payload stays small (`unread_count` + headlines + `person_github` + `href` + `collecting` + `collected_at`).

**DoD:** documented; dashboard can ignore this path and use `/api/me/since`. Optional settings page for a future extension token. **Do not build MV3 in this phase** — but the visit/refresh/ack rules above are the contract the extension must follow, so do not "simplify" by acking on GET.

---

### Phase 6 — Hosting (Docker on a VM, EC2 by default)

The API is a **long-running container**, not a serverless function. Docker is the unit of deploy so the same image runs on a laptop, EC2, Hetzner, or a friend's VPS.

| Layer | Pick | Work |
|---|---|---|
| API | **Docker on EC2** (t3.small is enough for v1) | `Dockerfile` + `docker-compose.yml`. `uvicorn` (or gunicorn+uvicorn workers) `:8080`. Host: Ubuntu, Docker Engine, optional Caddy for TLS. |
| Frontend | Vercel **or** `frontend` static build served by Caddy on the same VM | If split origins: `VITE_API_URL=https://api.example.com`, cookie `SameSite=None; Secure`. If same host: Caddy reverse-proxy `/api` and `/auth` to the API container, SPA on `/` — simpler cookies. |
| Database | Supabase, RDS, or **Postgres in Compose on the VM** | Alembic on boot or a `migrate` service. `postgresql+asyncpg` + SSL if remote. Compose Postgres is fine for a single-tenant v1; snapshot the volume. |
| Cron | **systemd timer on the VM** (preferred) | `curl -X POST https://localhost:8080/internal/run-pipeline?phase=collect` with `X-Cron-Secret`. Monday timer for `phase=narrate`. Hits loopback — no GitHub Actions required. Actions remain optional if you want logs in GitHub. |
| OAuth | GitHub OAuth App | Callback `https://<api-host>/auth/github/callback` |

**Dockerfile (API):** Python 3.11-slim, install deps, `CMD uvicorn app.main:app --host 0.0.0.0 --port 8080`. Multi-stage optional.

**docker-compose.yml (run anywhere):**

```yaml
services:
  api:
    build: .
    ports: ["8080:8080"]
    env_file: .env
    depends_on: [db]
    restart: unless-stopped
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: whatisup
      POSTGRES_PASSWORD: whatisup
      POSTGRES_DB: whatisup
    volumes: ["pgdata:/var/lib/postgresql/data"]
    restart: unless-stopped
volumes:
  pgdata:
```

Production EC2: copy `.env`, `docker compose up -d`, open 80/443 only, Caddy with Let's Encrypt. Security group: SSH from your IP, HTTP/S public.

**Explicitly not:** Cloud Run, Vercel Python functions, Fly as the API host of record. Frontend on Vercel is still optional.

**DoD:** `docker compose up` locally matches v0+v1 API. Same compose (or same image + remote `DATABASE_URL`) on EC2. systemd collect timer writes `pipeline_runs`. Login works. GitHub visit-triggered collect hits this VM (always on — no cold start).

---

### Phase 7 — Polish and v0 leftover cleanup

- Hide or gate `/admin` (builder flag).
- Remove unused `DigestDelivery` from UI (table can stay).
- Person page: keep template fallback when insight is `fallback*`.
- Stats: network-level this week, not global-all-owners.
- Error pages: GitHub rate limited, first-run empty network.
- `.env.example` updated; README: local OAuth (`http://localhost:8000/auth/github/callback` + Vite proxy or CORS).

---

## Frontend information architecture (v1)

```
/login                         GitHub OAuth
/                              Since last looked → Network story → Close circle → Highlights
/network                       All connections; ?tech= filter from story bullets
/person/:id                    Unchanged deep dive (only if connected to current owner)
/admin                         Builder-only pipeline trigger
```

Home must not be a grid of everyone. The user should not ask "where do I look?"

---

## LLM budget (free OpenRouter)

Assume ~50 people / owner / week:

- Per-person narratives: 50 calls (existing)
- Network story: **1 call**
- Since last looked: **0 calls** (templates)

If you hit 50 req/day, **tier**: skip LLM for people with `significance_total < 8` (template only); always run network story. Document in `run_narrate`.

---

## Grounding rules (non-negotiable)

1. Significance scoring stays a pure function. No LLM scoring.
2. Network rising/declining/new are SQL/counters. LLM may only rephrase `facts`.
3. "Since last looked" headlines are templates.
4. Do not feed last week's **prose** into this week's prompt. You may pass last week's **facts JSON** (counts only) into the network-story prompt for one comparison sentence, still validated against both payloads.
5. Personal interpretation ("they seem bored", "career pivot") is forbidden in prompts.

---

## Extension (after v1 API, not a v1 store listing)

The **visit loop is specified now** so the API is not designed around daily cron only. Ship MV3 after the hosted API exists.

- Content script: `https://github.com/*` (homepage, feed, profiles). On load + `visibilitychange` → `GET /api/me/highlights?refresh=1`. Paint badge from the JSON. If `collecting`, one delayed refetch.
- Profile page extra: if `username` is in the current highlight set, inject a small "N updates this week → pulse" chip.
- Popover / toolbar click: show the 3 items; `POST /api/me/ack`. Badge clears. Homepage-only inject never acks.
- `chrome.alarms` 15–30 min: same GET (covers time spent off GitHub). Still no ack.
- Auth: web login then `POST /api/me/extension-token`, or `chrome.identity.launchWebAuthFlow`.
- Shadow DOM for injected UI. Do not `setInterval` in a MV3 service worker.

v1 guarantees: highlights GET, refresh collect debounce, ack POST, CORS hook, Docker API that is awake when GitHub is opened.

---

## Suggested build order (calendar)

| Week | Phases |
|---|---|
| 1 | 0 + 1 (scheduler out, OAuth, scoped API, frontend login) |
| 2 | 2 + 3 (ETag collect, since-last-looked UI) |
| 3 | 4 (network facts + story + dashboard) |
| 4 | 5 + 6 + 7 (highlights contract, Docker/EC2, cleanup) |

---

## Verification plan

### Automated

```bash
pytest tests/ -v
```

New tests required: `test_since.py`, `test_network_facts.py`, `test_network_story_validation.py`, auth cookie 401s, pipeline lock.

### Manual (local)

1. Login with GitHub; following list matches GitHub.
2. Cannot `GET /api/owners/2/digest` for another id (gone or 403).
3. Trigger collect; second trigger mostly 304.
4. Plant a fixture external PR after `highlights_acked_at`; dashboard shows it in the top 3; **GET highlights again does not clear it**; `POST /api/me/ack` does.
5. Call `?refresh=1` twice within 15 minutes: only one collect starts.
6. Plant Kubernetes on 4 people this week, 1 in prior month; story reports rise; LLM disabled still shows template bullets.
7. Disconnect OpenRouter: person + network copy still render from templates.

### Manual (hosted)

1. `docker compose up -d` on EC2 (or local image against remote DB): login works.
2. systemd timer (or manual curl with cron secret) writes `pipeline_runs` `status=ok`.
3. Simulate many GitHub loads: highlights JSON updates `collected_at` at most every 15 minutes; `unread_count` does not drop until ack.

---

## v1 Definition of Done (product)

A signed-in user on the hosted app, on a weekday morning:

1. Sees up to three **since last visit** items, or a clear quiet state.
2. Sees a **network story** with countable, clickable bullets (techs, OSS firsts, quiet close circle) that match the database.
3. Can still open a person and see the v0 narrative + timeline.
4. Nobody else can read their network without their GitHub session.
5. API runs in Docker on a VM (EC2); nightly collect is a host timer; opening GitHub can refresh that owner's data at most every 15 minutes **without** clearing unread.

That is v1 full. Journeys, reconnect, parallel paths, four-way interestingness, and the Chrome Web Store listing start only after this DoD is true.
