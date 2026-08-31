# Pulse — PRD + Build SOP

**Working title:** Pulse (rename freely — used throughout this doc as a placeholder)
**Document type:** Combined Product Requirements Document + Standard Operating Procedure for build
**Audience:** an AI coding agent (Claude Code / Cursor / similar) building this from scratch
**Status:** v0 (no-auth) → v1 (auth, self-serve)

---

## 0. How to use this document

Build in the phase order given in Section 14. Each phase has a **Definition of Done** — do not start the next phase until the current one's DoD is met. If a requirement here is ambiguous, prefer the simpler interpretation that keeps v0 shippable; do not add scope that isn't explicitly listed. Section 5 is a hard list of things **not** to build yet — treat it as a guardrail, not a suggestion.

---

## 1. Problem statement (unchanged — anchor for every decision below)

Developers with growing technical networks struggle to stay aware of what the people they care about are building, learning, contributing to, and discussing, because technical activity is fragmented across platforms and presented as noisy, low-level events. Existing tools expose raw activity but do not aggregate, interpret, prioritize, and summarize it according to the user's relationships and interests.

The system solves this by: collecting public developer activity → normalizing it into structured events → scoring which events are actually significant → understanding what an individual is working on → prioritizing close connections over the broader network → surfacing significant developments network-wide → and presenting all of this as short, human-readable summaries, not raw event lists.

**Core thesis:** raw activity is not insight. "Ahmed pushed 3 commits" is not the product. "Ahmed has spent the last five days on a Kubernetes deployment and just opened his first PR to an external repo" is the product.

---

## 2. Product vision (one-liner)

A personal intelligence layer for a developer's technical network: tell the user what's happening across the people they follow on GitHub, prioritized by relationship and filtered down to what's actually significant.

---

## 3. Scope by stage

| Stage | Who uses it | How they get in | How they receive value |
|---|---|---|---|
| **v0 (this build)** | The builder + a handful of manually onboarded beta testers | Builder adds them by GitHub username via an admin-secret-protected endpoint or script — **no login of any kind** | Weekly digest, delivered by email (or console/markdown file during early dev) |
| **v1 (next, not this build)** | Self-serve users | GitHub OAuth login | Web dashboard + weekly digest |
| **v2+ (future, not this build)** | Same as v1 | — | Network-wide trend detection, natural-language query ("Ask Your Network"), additional sources beyond GitHub |

The schema and pipeline built in v0 must not require a rewrite to reach v1 — see Section 8's design note on this.

---

## 4. Goals for v0

1. Track a small number of GitHub identities (target: 15–50 people total across all testers) and ingest their public activity on a recurring schedule.
2. Turn raw events into a deterministic significance score — no LLM involved in this step.
3. Extract a lightweight technology profile per person from repo signals (files, topics, languages) — rule-based, no LLM.
4. Generate one short, grounded narrative paragraph per tracked person per week using an LLM, constrained so it cannot state anything not backed by the structured signals from steps 2–3.
5. Assemble a per-owner weekly digest (close circle first, then notable broader-network activity) and deliver it without requiring the recipient to log in anywhere.
6. Let the builder onboard a new tester in under a minute (one API call or script run, using the tester's GitHub username only).

## 5. Explicit non-goals for v0 — do not build these yet

- **No OAuth, no login, no session/auth middleware of any kind.** A single shared secret protects the admin endpoints; that is the only access control in v0.
- No web dashboard. A digest (email or a rendered markdown/HTML file) is the entire v0 UI.
- No job queue (Celery/Arq/Redis). A single in-process scheduler (APScheduler) is sufficient at this scale.
- No vector database, no embeddings, no semantic search.
- No natural-language query interface.
- No data sources beyond the GitHub REST API. No X/Twitter, no blogs, no Discord.
- No activity clustering / ML-based narrative generation beyond the single constrained LLM call in Section 9.5.
- No relationship scoring model. `is_close` is a boolean, set manually by the builder.
- No per-tester GitHub OAuth token. All GitHub API calls use one shared service token — see Section 7's note on why this works because only public data is read.

If a task isn't explicitly in Section 4 or Section 14, don't build it in this pass.

---

## 6. User stories

- As the builder, I want to add a tester by their GitHub username and have their network auto-populate from who they already follow on GitHub, so I don't have to manually collect a list from them.
- As the builder, I want to mark specific tracked people as "close circle" so their activity is never filtered out of the digest, even when it's minor.
- As a tester, I want a weekly email that tells me what my closest connections have been building, without needing to sign up for anything or check a dashboard.
- As the builder, I want to trigger a digest run on demand (not wait for the weekly schedule) so I can iterate on narrative quality during development.
- As the builder, I want every narrative sentence traceable back to a specific stored event, so I can catch and fix hallucinated claims before a tester ever sees them.

---

## 7. Architecture

```
                     ┌───────────────┐
                     │   Scheduler    │  (APScheduler, in-process)
                     └───────┬───────┘
                             │ weekly trigger (+ manual admin trigger)
                             ▼
┌──────────────┐     ┌───────────────┐      ┌──────────────┐
│  GitHub API   │◀───▶│    Worker      │─────▶│  LLM API     │
│ (public data) │     │ (FastAPI app,  │      │ (Anthropic)  │
└──────────────┘     │  same process  │      └──────────────┘
                     │  as the API    │
                     │  in v0)        │
                     └───────┬───────┘
                             │ reads/writes
                             ▼
                     ┌───────────────┐
                     │   Postgres     │
                     └───────────────┘
                             │
                             ▼
                     ┌───────────────┐
                     │ Email delivery │  (Resend, or console in dev)
                     └───────────────┘
```

**Why one shared GitHub token works with no auth:** every GitHub endpoint this project touches — user profiles, `following` lists, public events, public repos — is **public data**. Any authenticated token can read `GET /users/{username}/following` for *any* username; you don't need that person's own OAuth grant to see their public following list. This is what makes zero-auth onboarding possible: give us a username, we fetch what's already public.

**Tech stack:**

| Layer | Choice | Why |
|---|---|---|
| API/worker | FastAPI (Python, async) | Async-native for concurrent GitHub + LLM calls; Pydantic doubles as the LLM output schema |
| ORM/migrations | SQLModel or SQLAlchemy + Alembic | Standard, works identically once Postgres gains more tables in v1 |
| Database | Postgres (local via Docker Compose, or a free hosted instance like Neon/Supabase) | JSONB for flexible metadata now; room for `pgvector` later if v2 needs semantic search |
| Scheduling | APScheduler, in-process | No Redis/broker needed at this scale |
| LLM | Anthropic API, `claude-haiku-4-5-20251001` | Cheap and fast enough for a short, constrained per-person summary; $1/$5 per million input/output tokens as of this writing — a weekly run across 50 people costs well under $1 |
| Email delivery | Resend (or plain SMTP) | Minimal setup, generous free tier |
| Deployment (when ready) | Railway or Fly.io for the API+worker+Postgres; add Vercel + Next.js only in v1 for the dashboard | Avoid managing multiple platforms before there's a UI to deploy |

---

## 8. Data model

**Design note:** every table below is written so v1 (auth) is additive, not a rewrite. `owners` today is "whose digest is this" with no login; in v1 it gains `github_oauth_id` and a real session, but its primary key and every foreign key pointing to it stay exactly as they are.

```sql
-- owners: v0 stand-in for "user". No password, no OAuth fields yet.
CREATE TABLE owners (
    id              SERIAL PRIMARY KEY,
    label           TEXT NOT NULL,             -- e.g. "builder", "Priya"
    github_username TEXT,                       -- used once, to seed connections via /following
    delivery_email  TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- people: tracked GitHub identities. Global, not owned by any single owner —
-- two owners tracking the same person share one row (and one set of events/insights).
CREATE TABLE people (
    id                      SERIAL PRIMARY KEY,
    github_id               BIGINT UNIQUE NOT NULL,   -- GitHub's numeric id (stable across username changes)
    github_username         TEXT UNIQUE NOT NULL,
    display_name            TEXT,
    avatar_url              TEXT,
    profile_last_synced_at  TIMESTAMPTZ
);

-- connections: owner <-> person, many-to-many, with the close-circle flag.
CREATE TABLE connections (
    id         SERIAL PRIMARY KEY,
    owner_id   INTEGER NOT NULL REFERENCES owners(id),
    person_id  INTEGER NOT NULL REFERENCES people(id),
    is_close   BOOLEAN NOT NULL DEFAULT false,
    added_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner_id, person_id)
);

-- activity_events: normalized events, global per person.
CREATE TABLE activity_events (
    id                  SERIAL PRIMARY KEY,
    person_id           INTEGER NOT NULL REFERENCES people(id),
    source              TEXT NOT NULL DEFAULT 'github',
    external_event_id   TEXT NOT NULL,            -- GitHub's event id, for de-duplication
    event_type          TEXT NOT NULL,            -- see Section 9.2 for the enum
    repo_full_name       TEXT,
    occurred_at         TIMESTAMPTZ NOT NULL,
    raw_payload         JSONB NOT NULL,           -- original event, kept for debugging/audit
    metadata            JSONB,                    -- extracted signals: languages, topics, has_dockerfile, etc.
    significance_score  INTEGER NOT NULL DEFAULT 0,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, external_event_id)
);

-- technologies + person_technologies: rule-derived tech profile per person.
CREATE TABLE technologies (
    id    SERIAL PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL                    -- normalized, lowercase, e.g. "kubernetes"
);

CREATE TABLE person_technologies (
    person_id      INTEGER NOT NULL REFERENCES people(id),
    technology_id  INTEGER NOT NULL REFERENCES technologies(id),
    confidence     REAL NOT NULL DEFAULT 1.0,
    last_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (person_id, technology_id)
);

-- insights: one LLM-generated narrative per person per week. Global, reused across owners.
CREATE TABLE insights (
    id                     SERIAL PRIMARY KEY,
    person_id              INTEGER NOT NULL REFERENCES people(id),
    week_start             DATE NOT NULL,
    week_end               DATE NOT NULL,
    narrative_text         TEXT NOT NULL,
    supporting_event_ids   JSONB NOT NULL,        -- array of activity_events.id used as grounding
    significance_total     INTEGER NOT NULL,
    model_used             TEXT NOT NULL,
    generated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (person_id, week_start)
);

-- digest_deliveries: audit log of what was actually sent.
CREATE TABLE digest_deliveries (
    id                SERIAL PRIMARY KEY,
    owner_id          INTEGER NOT NULL REFERENCES owners(id),
    week_start        DATE NOT NULL,
    content_snapshot  TEXT NOT NULL,
    delivery_method   TEXT NOT NULL,               -- 'email' | 'console'
    status            TEXT NOT NULL,               -- 'sent' | 'failed'
    delivered_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 9. Pipeline specification

### 9.1 Collection

- Use one shared GitHub personal access token (`GITHUB_TOKEN` env var), scopes: `public_repo`, `read:user` — read-only, no write scopes.
- On tester onboarding: call `GET /users/{username}/following` to seed `people` + `connections` rows (`is_close = false` by default).
- On each polling cycle (recommend: once daily, well under the 5,000 req/hr authenticated limit for the scale in Section 4): for every row in `people`, call `GET /users/{username}/events/public` and upsert repo metadata (`GET /repos/{owner}/{repo}` for topics/language when a new repo is seen).
- Respect `X-RateLimit-Remaining` / `X-RateLimit-Reset` response headers; back off when remaining drops below a safety margin (e.g. 100).

### 9.2 Normalization

Map each raw GitHub event `type` to one row in `activity_events` with a normalized `event_type`:

| GitHub event type | Normalized `event_type` |
|---|---|
| `PushEvent` | `push` |
| `CreateEvent` (ref_type = repository) | `repository_created` |
| `PullRequestEvent` (action = opened) | `pull_request_opened` |
| `PullRequestEvent` (action = closed, merged = true) | `pull_request_merged` |
| `IssuesEvent` (action = opened) | `issue_opened` |
| `ReleaseEvent` (action = published) | `release_published` |
| `ForkEvent` | `fork` |

Use `external_event_id` (GitHub's event `id`) for the unique constraint so re-polling never double-inserts.

### 9.3 Significance scoring (deterministic — no LLM)

Starting weights (tune after real data — these are a reasonable default, not fixed):

| Event | Score |
|---|---|
| Routine push (no other signal) | 1 |
| Dependency-only / typo-only commit (detected via commit message keywords: `bump`, `typo`, `fix readme`, `update deps`) | 0 |
| New repository created | 5 |
| First public repository ever for that person | 15 |
| Pull request opened, own repo | 3 |
| Pull request opened, external repo (not owned by the person) | 10 |
| Pull request merged, external repo | 12 |
| Release published | 8 |
| Repository reactivated after 90+ days dormant | 6 |
| First contribution to a new organization | 15 |

Weekly `significance_total` for a person = sum of that week's event scores. Suggested digest thresholds: close-circle people always appear (score just changes ranking within the section); broader-network people need `significance_total >= 15` to appear as a "network highlight."

### 9.4 Technology extraction (rule-based — no LLM)

| Signal | Technology |
|---|---|
| `Dockerfile` at repo root | Docker |
| `helm/` or `charts/` directory present | Kubernetes |
| Repo topic tag | Direct mapping (lowercase the topic string) |
| Repo primary language (from GitHub repo metadata) | Direct mapping |
| `go.mod` present | Go |
| `requirements.txt` or `pyproject.toml` present | Python |
| `package.json` present | Node.js |

Write each match into `person_technologies` with a `confidence` (1.0 for topic/language, 0.7 for file-pattern signals) and update `last_seen_at`.

### 9.5 Weekly narrative generation (the only LLM step)

**Model:** `claude-haiku-4-5-20251001` via the Anthropic Python SDK (`anthropic` package). One call per person per week — never per raw event.

**Output schema (Pydantic):**

```python
class WeeklyNarrative(BaseModel):
    narrative: str                     # 1-3 plain sentences
    technologies_mentioned: list[str]  # must be a subset of provided person_technologies
    supporting_event_ids: list[int]    # must be a subset of the event ids provided in the prompt
```

**System prompt (draft — refine wording during dogfooding, keep the rules):**

```
You are writing a short weekly update about a developer's public GitHub
activity for someone who knows them personally or professionally.

You will be given:
- The person's username and display name.
- A list of this week's normalized activity events (type, repo, timestamp,
  and any extracted signals such as detected languages or file markers).
- A list of technologies already associated with this person, with confidence.

Rules:
1. Only state facts directly supported by the provided events or technology
   list. Do not infer intentions, plans, or projects that aren't evidenced.
2. If activity is sparse or purely routine (dependency bumps, typo fixes,
   formatting), say so plainly rather than inflating it into a narrative.
3. Only name a technology if it appears in the provided technology list, or
   is directly evidenced by a signal in this week's events.
4. Write 1-3 sentences. Plain language. No marketing tone, no speculation.
5. Return only the JSON object matching the given schema. No other text.
```

**Server-side validation (required, not optional):** after generation, check that every item in `technologies_mentioned` exists in that person's `person_technologies` rows, and every id in `supporting_event_ids` exists in the event ids passed into the prompt. If either check fails, discard the output and fall back to a templated line (e.g. `"{name} had routine activity this week — no major changes detected."`) rather than retrying indefinitely. Log every fallback for manual review; a high fallback rate signals the prompt needs work, not that the check should be loosened.

### 9.6 Digest assembly and delivery

For a given `owner_id` and `week_start`:
1. Fetch all `connections` for the owner, joined to the week's `insights` for each `person_id`.
2. Split into **Close Circle** (all `is_close = true` connections, regardless of score) and **Network Highlights** (`is_close = false` connections with `significance_total >= 15`, sorted descending).
3. Render as a short plain-text or simple-HTML email: person name, one narrative line, optionally a link to their GitHub profile.
4. Send via Resend (or SMTP); on failure, log to `digest_deliveries` with `status = 'failed'` and retry once before giving up for that owner that week.
5. During early development (Phase 6–7 below), skip real delivery and just print the rendered digest to console / write it to a local markdown file — wire up real email only once narrative quality is verified.

---

## 10. API surface for v0

No user-facing API is required yet (delivery is push-based, via email). Admin endpoints, protected by comparing an `X-Admin-Secret` header against the `ADMIN_SECRET` env var:

| Method & path | Purpose |
|---|---|
| `POST /admin/owners` | Body: `{label, github_username, delivery_email}`. Creates the owner, calls `/following` to seed `people` + `connections`. |
| `PATCH /admin/connections/{id}` | Body: `{is_close: true|false}`. Toggle close-circle status. |
| `POST /admin/run-digest?owner_id=...` | Manually trigger a digest build+send for one owner, bypassing the weekly schedule — for testing. |
| `GET /health` | Basic liveness check, unauthenticated. |

A CLI script under `scripts/` doing the same thing is an acceptable substitute for the first two endpoints if that's faster to build first.

---

## 11. Repo structure

```
pulse/
├── app/
│   ├── main.py                 # FastAPI app entrypoint
│   ├── config.py                # env var loading (pydantic-settings)
│   ├── db.py                    # SQLAlchemy engine/session
│   ├── models/                  # one file per table from Section 8
│   ├── github/
│   │   ├── client.py             # rate-limit-aware GitHub REST wrapper
│   │   ├── collector.py          # fetch events/profiles/following
│   │   └── normalize.py          # raw event -> activity_events mapping (9.2)
│   ├── scoring/
│   │   ├── significance.py       # 9.3
│   │   └── technology.py         # 9.4
│   ├── narrative/
│   │   ├── prompts.py            # 9.5 system prompt
│   │   ├── generate.py           # LLM call + validation + fallback
│   │   └── schema.py             # WeeklyNarrative Pydantic model
│   ├── digest/
│   │   ├── build.py               # 9.6 assembly
│   │   └── deliver.py             # email/console delivery
│   ├── routers/
│   │   ├── admin.py                # Section 10 endpoints
│   │   └── health.py
│   └── scheduler.py                # APScheduler weekly job
├── alembic/                         # migrations
├── scripts/
│   ├── add_owner.py                 # CLI alternative to POST /admin/owners
│   └── run_digest_now.py            # local manual trigger
├── tests/
│   ├── test_significance.py
│   ├── test_normalize.py
│   └── test_narrative_validation.py
├── docker-compose.yml                # local Postgres
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 12. Environment variables

```
DATABASE_URL=postgresql://...
GITHUB_TOKEN=ghp_...              # read-only scopes: public_repo, read:user
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
ADMIN_SECRET=...                   # random string; sent as X-Admin-Secret header
RESEND_API_KEY=...                 # optional until Phase 7b
DIGEST_FROM_EMAIL=pulse@yourdomain.example
```

---

## 13. Success metrics / exit criteria for v0

Move to v1 only once:
- The builder has read at least 3 consecutive weekly digests about their own network and each contained at least one thing they didn't already know.
- A manual spot-check of a full week's narratives shows zero unsupported claims (the grounding validation in 9.5 should make this true by construction — treat any failure as a bug, not an acceptable miss).
- At least 3 of the first 5 beta testers are still opening/reading the digest by week 3 (a one-line "still finding this useful? y/n, reply to let me know" in the email footer is enough signal — no analytics infra needed).

---

## 14. Build SOP — phases

Work through these in order. Each phase lists its objective, the concrete tasks, and a Definition of Done.

### Phase 0 — Scaffolding
**Objective:** a runnable, empty FastAPI app with Postgres.
**Tasks:** initialize the repo structure from Section 11; `docker-compose.yml` for local Postgres; `pyproject.toml` with `fastapi`, `sqlalchemy` (or `sqlmodel`), `alembic`, `httpx`, `apscheduler`, `anthropic`, `pydantic-settings`, `python-dotenv`; `.env.example` from Section 12; `GET /health` returns 200.
**Done when:** `uvicorn app.main:app` runs locally, `/health` returns 200, Postgres is reachable.

### Phase 1 — Data models & migrations
**Objective:** every table in Section 8 exists.
**Tasks:** define SQLAlchemy/SQLModel models exactly matching Section 8's schema; generate and apply the first Alembic migration.
**Done when:** all seven tables exist in the local Postgres instance with correct types and constraints (including the `UNIQUE` constraints).

### Phase 2 — GitHub collector
**Objective:** pull real data for a real GitHub username.
**Tasks:** `github/client.py` wraps `httpx` with the shared token, reads rate-limit headers, backs off near the limit; `github/collector.py` implements `fetch_following(username)`, `fetch_public_events(username)`, `fetch_repo_metadata(owner, repo)`.
**Done when:** running the collector against your own GitHub username returns a real following list and a real events list, printed or logged.

### Phase 3 — Normalization
**Objective:** raw GitHub events become `activity_events` rows.
**Tasks:** implement the mapping table from 9.2; insert with the `UNIQUE(source, external_event_id)` constraint so re-runs don't duplicate.
**Done when:** running the collector + normalizer twice in a row against the same username produces the same row count the second time (no duplicates), and `test_normalize.py` covers at least one case per event type in the mapping table.

### Phase 4 — Significance scoring
**Objective:** every `activity_events` row gets a `significance_score`.
**Tasks:** implement the rule table from 9.3 as a pure function `score_event(event) -> int`; apply it during normalization or as a follow-up pass.
**Done when:** `test_significance.py` asserts the exact score for one example of each rule in the table.

### Phase 5 — Technology extraction
**Objective:** `person_technologies` gets populated.
**Tasks:** implement the rule table from 9.4; run it whenever new repo metadata is fetched.
**Done when:** running it against a repo you know contains a Dockerfile and a `go.mod` correctly extracts Docker and Go with the expected confidence values.

### Phase 6 — Weekly narrative generation
**Objective:** one grounded paragraph per person per week.
**Tasks:** implement `narrative/prompts.py`, `narrative/schema.py`, `narrative/generate.py` per Section 9.5, including the mandatory server-side validation and fallback.
**Done when:** running it against your own tracked people produces narratives you'd actually want to read, `test_narrative_validation.py` proves the validation rejects a deliberately-broken fixture (a technology or event id not in the provided context), and the fallback path is exercised by at least one test.

### Phase 7a — Console/file digest (before email)
**Objective:** see a full digest end to end, cheaply.
**Tasks:** implement `digest/build.py` per Section 9.6; render to console or a local markdown file. Do not wire up email yet.
**Done when:** `scripts/run_digest_now.py --owner_id 1` prints a digest that correctly separates Close Circle from Network Highlights and matches what's in the database.

### Phase 7b — Real delivery
**Objective:** the digest reaches an inbox.
**Tasks:** implement `digest/deliver.py` with Resend (or SMTP); log every send to `digest_deliveries`.
**Done when:** you receive your own digest by email, and a deliberately-failed send (e.g. bad API key) is logged with `status = 'failed'` rather than crashing the run.

### Phase 8 — Scheduling & admin
**Objective:** it runs itself, and testers can be added without touching the database directly.
**Tasks:** `scheduler.py` registers a weekly APScheduler job calling the same digest-build-and-send path as Phase 7b, for every active owner; implement the Section 10 admin endpoints (or the equivalent CLI scripts), guarded by `X-Admin-Secret`.
**Done when:** `POST /admin/owners` with a real GitHub username results in a populated `connections` list within seconds, and the scheduler fires on its own without manual triggering (verify by temporarily setting a short interval in dev).

### Phase 9 — Dogfood pass
**Objective:** validate the product, not just the code.
**Tasks:** onboard yourself and 2-4 willing testers; let it run for at least 3 real weeks; track the Section 13 exit criteria.
**Done when:** the Section 13 criteria are met, or you've learned something specific enough to revise Sections 9.3/9.5's rules and prompt before continuing.

### Phase 10 — v1 upgrade path (do not build yet — plan only)
When Phase 9 validates the idea: add GitHub OAuth login (`owners` gains `github_oauth_id`, session handling); build the Next.js dashboard reading the same `insights`/`connections` tables; let logged-in owners manage their own `is_close` flags and trigger their own following-sync instead of the builder doing it manually; keep the weekly email as an option alongside the dashboard rather than replacing it. No schema table from Section 8 should need to be dropped or restructured to get here.

---

## 15. Testing strategy

- Unit tests are required for Sections 9.2 (normalization), 9.3 (scoring), and 9.5's validation logic (Phase 3, 4, 6 Definitions of Done above) — these are the parts most likely to silently produce wrong output.
- Manual QA each phase against your own real GitHub account before moving on; synthetic/fixture data alone will hide GitHub API quirks (pagination, missing fields on some event types, rate-limit headers).
- No end-to-end browser testing is needed for v0 — there's no browser UI yet.

---

## 16. Risks & open questions

- **Rate limit ceiling:** 5,000 authenticated requests/hour, shared across all owners on one token. At roughly 3-5 requests per tracked person per polling cycle, that supports on the order of 1,000+ people polled once daily before a second token or less frequent polling is needed — comfortably above v0's target scale.
- **LLM hallucination:** mitigated by the mandatory grounding validation in 9.5, not by prompt wording alone. Do not skip the validation step to save development time.
- **Third-party privacy:** tracked people never opted in, even though the data is public. Before onboarding testers beyond a small trusted group, add a simple opt-out mechanism (an unlisted page any GitHub user can use to request removal) and re-check GitHub's API Terms of Service for acceptable use.
- **Cost:** at Haiku 4.5 pricing ($1/$5 per million input/output tokens), a weekly run across 50 tracked people costs well under $1/week — recheck current pricing before scaling tester count meaningfully, since rates change.

---

## Appendix A — example significance scoring test cases

```python
def test_new_repository_created():
    assert score_event(make_event("repository_created")) == 5

def test_first_repository_ever():
    assert score_event(make_event("repository_created", is_first_repo=True)) == 15

def test_external_pr_merged():
    assert score_event(make_event("pull_request_merged", is_external=True)) == 12

def test_dependency_bump_scores_zero():
    assert score_event(make_event("push", commit_message="bump lodash to 4.17.21")) == 0
```

## Appendix B — example narrative validation test case

```python
def test_rejects_ungrounded_technology():
    output = WeeklyNarrative(
        narrative="Ahmed has been building a Rust game engine.",
        technologies_mentioned=["rust"],   # not in the provided person_technologies fixture
        supporting_event_ids=[101, 102],
    )
    assert not passes_grounding_check(output, allowed_technologies={"python", "docker"}, allowed_event_ids={101, 102})
```
