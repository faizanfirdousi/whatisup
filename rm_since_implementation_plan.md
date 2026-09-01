# Transform WhatIsUp: From Activity Counter to Network Intelligence

The homepage currently displays aggregated GitHub telemetry (event counts, raw scores, person grids). This plan rewrites it to surface **interpreted intelligence** — story cards, "why it matters" context, time-period selection, network-level patterns, and editorial restraint.

## User Review Required

> [!IMPORTANT]
> **Time Period Selector** — The current system is locked to "current calendar week." This plan adds a selectable time range (7d / 14d / 30d / this week) across the digest, story, and stats endpoints. This changes the semantics of several API responses. Please confirm the default you want: `7d` rolling or `this_week` (Monday–Sunday)?

> [!IMPORTANT]
> **"Since you last visited" — Kill or Fix?** Your analysis offers two options. This plan implements **Option B (replace with "Worth your attention")** for now, since proper `last_seen_at` tracking is already in place via `highlights_acked_at`. The existing ack mechanism will continue to work underneath, but the section title and empty-state copy will change. If you want Option A (full persistent last-seen tracking with deferred ack), call it out.

> [!WARNING]
> **Narrative quality dependency** — Points 4–5 (headline + summary + why_it_matters) require the LLM narrative output schema to change. The existing `WeeklyNarrative` Pydantic model gains new fields. Narratives already stored in the DB will be rendered via template fallback until the pipeline regenerates them. Old insights won't break, but they'll look simpler until the next pipeline run.

## Open Questions

> [!IMPORTANT]
> **Score visibility** — The plan removes the numeric "Score: 667" badge entirely from PersonCard and InsightCard. Do you want to keep it available somewhere (e.g., a tooltip, or on the person detail page only)?

> [!IMPORTANT]
> **Homepage story limit** — The plan defaults to showing the top 5 story cards on the homepage. Do you want a different cap, or an expandable "Show more" that loads additional cards?

---

## Proposed Changes

The work is organized into 6 phases that can be shipped incrementally. Each phase is independently deployable.

---

### Phase 1 — Backend: Enriched Narrative Schema + Time Period Support

This is the foundation that everything else builds on. We change what the backend computes and serves.

---

#### [MODIFY] [schema.py](file:///home/faizan/projects/whatisup/app/narrative/schema.py)

Extend `WeeklyNarrative` with new fields for richer frontend rendering:

```python
class WeeklyNarrative(BaseModel):
    headline: str                          # NEW — 1-line attention grabber
    narrative: str                         # existing — 1-3 sentence summary
    why_it_matters: str | None = None      # NEW — grounded interpretation
    technologies_mentioned: list[str]
    supporting_event_ids: list[int]
    focus_area: str | None = None          # NEW — e.g. "observability", "infrastructure"
    activity_type: str | None = None       # NEW — e.g. "external_contribution", "release", "new_project"
```

#### [MODIFY] [prompts.py](file:///home/faizan/projects/whatisup/app/narrative/prompts.py)

Update `SYSTEM_PROMPT` to instruct the LLM to generate `headline`, `why_it_matters`, `focus_area`, and `activity_type` alongside the existing narrative. Add explicit grounding rules for `why_it_matters` — it must only reference observable patterns, never infer intent.

#### [MODIFY] [generate.py](file:///home/faizan/projects/whatisup/app/narrative/generate.py)

Update the structured output schema sent to OpenRouter. The response parsing and `sanitize_narrative` will handle the new fields, falling back to `None` for old-format responses.

#### [MODIFY] [template.py](file:///home/faizan/projects/whatisup/app/narrative/template.py)

Update `template_narrative` to also return `headline` and `why_it_matters` via deterministic rules. For example:
- headline: `"{name} is going deeper into {top_tech}"` or `"{name} shipped a release"`
- why_it_matters: `"Multiple external contributions suggest growing involvement in open-source {tech} ecosystem"` — only when evidence supports it.

#### [MODIFY] [dashboard.py](file:///home/faizan/projects/whatisup/app/routers/dashboard.py)

- **Add `period` query parameter** to `/api/me/digest` and `/api/me/stats` — accepts `7d`, `14d`, `30d`, `this_week`. Default: `7d`.
- Compute lookback window from the period parameter instead of hardcoded `ACTIVITY_LOOKBACK_DAYS = 30`.
- Change `_person_payload` to include the enriched narrative fields (`headline`, `why_it_matters`, `focus_area`, `activity_type`).
- **Remove** raw `significance_total` from top-level person payload (keep it internal for ranking only).
- **Add** a `meaningful_changes` count per person — count of events with `significance_score >= 5`.

#### [NEW] [digest_v2.py](file:///home/faizan/projects/whatisup/app/routers/digest_v2.py)

New endpoint: `GET /api/me/digest/v2?period=7d` that returns the redesigned structure:

```json
{
  "greeting": "Good morning, Faizan",
  "period": "7d",
  "summary": {
    "meaningful_changes": 7,
    "people_shipped": 3,
    "new_projects": 2,
    "interesting_repos": 1
  },
  "stories": [
    {
      "id": "story:person:42",
      "type": "person_story",
      "headline": "Atharva is going deeper into observability",
      "summary": "Worked across OpenTelemetry and KServe-related repositories...",
      "why_it_matters": "Noticeable shift toward cloud-native infrastructure work",
      "person": { "id": 42, "github_username": "...", "avatar_url": "..." },
      "technologies": ["opentelemetry", "kserve", "go"],
      "activity_type": "external_contribution",
      "rank": 45
    }
  ],
  "close_circle": [
    {
      "person": { ... },
      "current_focus": "Kubernetes portfolio infrastructure",
      "meaningful_changes": 2,
      "active_repos": ["repo1", "repo2"]
    }
  ],
  "network_pulse": {
    "more_active": 8,
    "steady": 14,
    "quiet": 14,
    "top_technologies": [
      {"name": "kubernetes", "direction": "up", "people_count": 5},
      {"name": "go", "direction": "up", "people_count": 4}
    ]
  },
  "emerging": [
    {
      "type": "tech_cluster",
      "headline": "Observability is becoming more common across your network",
      "technologies": ["opentelemetry", "prometheus"],
      "people_count": 4
    },
    {
      "type": "shared_repo",
      "headline": "3 people interacted with nudgebee/nudgebee",
      "repo": "nudgebee/nudgebee",
      "people_count": 3
    }
  ]
}
```

---

#### [MODIFY] [me.py](file:///home/faizan/projects/whatisup/app/routers/me.py)

- Add `period` query parameter to `/api/me/since` and `/api/me/highlights`.
- Rename the section concept from "Since you last looked" to "Worth your attention" in response payloads.
- Change `empty_copy` from the current pipeline-exposing message to: `"No meaningful changes yet. We'll highlight changes here as your network becomes active."`

#### [MODIFY] [network_story.py (narrative)](file:///home/faizan/projects/whatisup/app/narrative/network_story.py)

- Extend `NetworkStoryOut` with:
  - `network_pulse: dict` — `{ more_active, steady, quiet }` counts
  - `top_technologies: list[dict]` — tech with direction (up/down/steady)
  - `shared_repos: list[dict]` — repos where ≥2 people interacted
- Update `template_network_story` to compute these from existing `facts`.
- Update `NETWORK_STORY_PROMPT` to include these in the LLM output.

#### [MODIFY] [facts.py](file:///home/faizan/projects/whatisup/app/network/facts.py)

- Add `shared_repos` computation: repos where ≥2 tracked people have events this period.
- Add `activity_direction` per person: compare this period's event count to the prior period.
- Accept a `period_days` parameter (default 7) instead of always using `current_week_bounds`.
- Add `people_by_activity_level` bucketing: `more_active` (events this period > prior period), `steady`, `quiet` (zero events).

#### [MODIFY] [since.py](file:///home/faizan/projects/whatisup/app/scoring/since.py)

- Remove internal scoring jargon from user-facing headlines. Instead of `"significance 12 · close circle"`, generate readable reasons like `"First tracked contribution to an external project"`.
- Change `headline` generation to use story-oriented language.

---

### Phase 2 — Frontend: New Homepage Architecture

Complete rewrite of the Dashboard page, replacing the current stats + grid layout with the intelligence-first design.

---

#### [MODIFY] [client.js](file:///home/faizan/projects/whatisup/frontend/src/api/client.js)

Add new API methods:
```javascript
getDigestV2: (period = '7d') => fetchApi(`/me/digest/v2?period=${period}`),
```

#### [NEW] [PeriodSelector.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/PeriodSelector.jsx)

Segmented control component with options: `7 days` | `14 days` | `30 days` | `This week`. Emits the selected period string. Persists selection to `localStorage`.

#### [NEW] [HeroBanner.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/HeroBanner.jsx)

Top section replacing `StatsBar`. Shows:
- Personalized greeting with time of day
- Period selector
- Summary line: **"7 meaningful changes across 36 people"**
- 3 interpretive sub-stats: "3 new external contributions · 2 releases · 4 people exploring new technologies"

No raw counts. No "Weekly Insights: 4".

#### [NEW] [StoryCard.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/StoryCard.jsx)

The new atomic unit of the homepage. Replaces `PersonCard` on the homepage. Structure:

```
┌─────────────────────────────────────────────┐
│  ↑ ACTIVITY_TYPE badge          [avatar]    │
│                                             │
│  HEADLINE (large, bold)                     │
│  Summary paragraph (2-3 lines)              │
│                                             │
│  Tech badges: [OpenTelemetry] [Go] [K8s]    │
│                                             │
│  ┌─ Why it matters ──────────────────────┐  │
│  │ Grounded interpretation sentence      │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [View person →]                            │
└─────────────────────────────────────────────┘
```

#### [NEW] [CloseCircleCard.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/CloseCircleCard.jsx)

Visually distinct from StoryCard. Shows:
- Person name + avatar
- "Currently focused on: {focus_area}"
- "{N} meaningful changes" (not event count)
- Active repositories (max 3)
- Link to full person detail

#### [NEW] [NetworkPulse.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/NetworkPulse.jsx)

Replaces the bottom person grid. Visual summary:
```
↑ More active: 8 people
→ Steady: 14 people  
↓ Quiet: 14 people

Top technologies: Kubernetes ↑  Go ↑  Python →  AI ↑
```

#### [NEW] [EmergingPatterns.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/EmergingPatterns.jsx)

Network-level intelligence section:
- Tech clusters: "Observability is becoming more common across your network"
- Shared repos: "3 people interacted with nudgebee/nudgebee"
- Rising/declining trends from `facts.rising` and `facts.declining`

#### [MODIFY] [Dashboard.jsx](file:///home/faizan/projects/whatisup/frontend/src/pages/Dashboard.jsx)

Complete rewrite. New structure:
1. `<HeroBanner>` — greeting + summary + period selector
2. `<section>` "Worth your attention" — top 3-5 `<StoryCard>`s (replaces SinceLastLooked)
3. `<section>` "Close Circle" — `<CloseCircleCard>` for each close connection
4. `<NetworkPulse>` — activity bucketing + tech trends
5. `<EmergingPatterns>` — network-level patterns
6. Footer link: "Explore full network →" (links to /network)

**Removed from homepage**: `<StatsBar>`, `<PersonGrid>` for all 36 people, `<SinceLastLooked>`, raw "Rest of network" grid.

---

### Phase 3 — Frontend: Kill Raw Scores & Improve Empty States

---

#### [MODIFY] [PersonCard.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/PersonCard.jsx)

- **Remove** the `Score: {score}` badge entirely.
- Replace with activity-type indicator (e.g., a small colored dot or label like "Active" / "Shipped" / "Contributing").
- Keep narrative text and top repos.

#### [MODIFY] [InsightCard.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/InsightCard.jsx)

- **Remove** `Score {insight.significance_total}` badge.
- **Remove** `{insight.model_used}` display (users don't care which LLM generated this).
- Add `headline` display (large) above the narrative.
- Add `why_it_matters` section below the narrative if present.

#### [MODIFY] [SinceLastLooked.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/SinceLastLooked.jsx)

Rename to **WorthAttention.jsx** (or simply modify in place):
- Title: "Worth your attention" instead of "Since you last looked"
- Empty state: "Nothing worth surfacing yet. We'll highlight meaningful changes here as your network becomes active." — **never mention the pipeline**.
- Remove the `"significance {score}"` from item `reason` text.

#### [MODIFY] [NetworkStory.jsx](file:///home/faizan/projects/whatisup/frontend/src/components/NetworkStory.jsx)

- Add the `network_pulse` visualization (activity bucketing bars).
- Add `shared_repos` display.
- Replace generic "Your network was quiet" with better empty state.

---

### Phase 4 — Frontend: Premium Visual Polish

---

#### [MODIFY] [index.css](file:///home/faizan/projects/whatisup/frontend/src/index.css)

Add new CSS classes for the redesigned components:
- `.story-card` — larger glass card with left accent border
- `.hero-banner` — gradient background panel with animated mesh
- `.pulse-bar` — horizontal bar visualization for network pulse
- `.close-circle-card` — distinct visual treatment (softer border, different bg tint)
- `.period-selector` — segmented control styling
- `.emerging-card` — subtle card with pattern/tech cluster indicators
- `.why-it-matters` — highlighted box within story cards
- `.activity-badge` — replaces score badge (uses activity_type colors)
- Micro-animations: card entrance (staggered fade-up), pulse bar fill, badge shimmer
- Responsive adjustments: story cards go full-width on mobile

---

### Phase 5 — Backend: Week-over-Week Change Detection

---

#### [MODIFY] [facts.py](file:///home/faizan/projects/whatisup/app/network/facts.py)

Add `compute_person_trend(session, person_id, period_days)` that returns:
```python
{
  "direction": "up" | "down" | "steady",
  "this_period_events": 17,
  "prior_period_events": 5,
  "change_pct": 240,
  "new_repos": ["org/new-repo"],
  "new_techs": ["kserve"],
  "focus_shift": "personal → open-source"  # optional, only if pattern detected
}
```

This powers:
- The `activity_direction` per person in the digest
- The "Network Pulse" activity bucketing
- Trend arrows on story cards

#### [MODIFY] [dashboard.py](file:///home/faizan/projects/whatisup/app/routers/dashboard.py) (or `digest_v2.py`)

Include trend data in story payloads when available. Add `trend` field to each person's story card data.

---

### Phase 6 — Network Page Enhancement

---

#### [MODIFY] [Network.jsx](file:///home/faizan/projects/whatisup/frontend/src/pages/Network.jsx)

The Network page becomes the "explore everyone" view:
- Add search/filter bar (by name, tech, activity level)
- Group people by activity level (Active / Steady / Quiet) instead of a flat grid
- Show mini story headline on each card instead of just avatar + toggle
- Move the full person grid here (it was removed from the homepage)

---

## Verification Plan

### Automated Tests

```bash
# Existing tests should still pass
cd /home/faizan/projects/whatisup && python -m pytest tests/ -v

# New tests for enriched narrative schema
python -m pytest tests/test_narrative_validation.py -v

# Test the new digest_v2 endpoint structure
python -m pytest tests/test_digest_v2.py -v
```

### Manual Verification

1. **Backend first**: Run the pipeline, then hit `/api/me/digest/v2?period=7d` and verify the response structure matches the spec above.
2. **Frontend visual**: Start the dev server (`npm run dev`), load the homepage, verify:
   - Greeting with period selector renders
   - Story cards appear (max 5) with headline + summary + why_it_matters
   - Close circle shows focus area, not event counts
   - Network pulse shows activity bucketing
   - No raw "Score: X" anywhere on the homepage
   - Empty states are human, never mention "pipeline"
3. **Period selector**: Switch between 7d/14d/30d and verify data changes.
4. **Responsive**: Check mobile layout — story cards stack, pulse bars resize.
5. **Edge cases**: Test with a network that has zero events (clean empty state), and with a single-person close circle.
