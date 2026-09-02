-- EXPLAIN ANALYZE helpers for /api/me/digest/v2 query patterns.
-- Run against production-like data with psql or Supabase SQL editor.
-- Replace :owner_id and :person_ids with real values from your database.

-- 1. Connections for owner (digest route)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT connections.*
FROM connections
WHERE connections.owner_id = :owner_id;

-- 2. Activity events for digest window (prior_start .. end_dt)
-- prior_start = period_start - max(28, period_days)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT activity_events.id, activity_events.person_id, activity_events.event_type,
       activity_events.repo_full_name, activity_events.occurred_at,
       activity_events.significance_score, activity_events.metadata_
FROM activity_events
WHERE activity_events.person_id = ANY(:person_ids)
  AND activity_events.occurred_at >= :prior_start
  AND activity_events.occurred_at <= :end_dt
ORDER BY activity_events.occurred_at DESC;

-- 3. Latest insight per person (DISTINCT ON)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT DISTINCT ON (insights.person_id) insights.*
FROM insights
WHERE insights.person_id = ANY(:person_ids)
ORDER BY insights.person_id, insights.week_start DESC;

-- 4. Person technologies (network facts)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT person_technologies.*, technologies.name
FROM person_technologies
JOIN technologies ON technologies.id = person_technologies.technology_id
WHERE person_technologies.person_id = ANY(:person_ids);

-- 5. Historical external PR lookup (conditional)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT activity_events.person_id, activity_events.repo_full_name,
       activity_events.metadata_, people.github_username
FROM activity_events
JOIN people ON people.id = activity_events.person_id
WHERE activity_events.person_id = ANY(:pr_person_ids)
  AND activity_events.event_type IN ('pull_request_opened', 'pull_request_merged')
  AND activity_events.occurred_at < :period_start;

-- Look for Seq Scan on large tables; verify index usage on:
--   activity_events (person_id, occurred_at)
--   connections (owner_id) — may need dedicated index if seq scan appears
--   insights (person_id, week_start)
