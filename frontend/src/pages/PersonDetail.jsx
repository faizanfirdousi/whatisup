import React from 'react';
import { useParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { api } from '../api/client';
import { Loader } from '../components/Loader';
import { InsightCard } from '../components/InsightCard';
import { EventTimeline } from '../components/EventTimeline';
import { TechBadge } from '../components/TechBadge';

export function PersonDetail() {
  const { id } = useParams();
  const { data: person, loading, error } = useApi(api.getPerson, [id]);
  const { data: events, loading: eventsLoading } = useApi(api.getPersonEvents, [id]);

  if (loading || eventsLoading) return <Loader />;
  if (error) return <div className="glass-panel" style={{ padding: '2rem' }}>{error}</div>;
  if (!person) return null;

  return (
    <div>
      <header style={{ display: 'flex', gap: '1.25rem', alignItems: 'center', marginBottom: '2rem' }}>
        <img
          src={person.avatar_url || `https://github.com/${person.github_username}.png`}
          alt={person.github_username}
          style={{ width: '72px', height: '72px', borderRadius: '50%' }}
        />
        <div>
          <h1 style={{ fontSize: '2rem' }}>{person.display_name || person.github_username}</h1>
          <a href={`https://github.com/${person.github_username}`} target="_blank" rel="noreferrer">
            @{person.github_username}
          </a>
        </div>
      </header>

      <section style={{ marginBottom: '2rem' }}>
        <h2 style={{ marginBottom: '1rem' }}>Technologies</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {(person.technologies || []).length === 0 ? (
            <span style={{ color: 'var(--text-tertiary)' }}>None extracted yet.</span>
          ) : (
            person.technologies.map((t) => (
              <TechBadge key={t.name} name={t.name} confidence={t.confidence} />
            ))
          )}
        </div>
      </section>

      <section style={{ marginBottom: '2rem' }}>
        <h2 style={{ marginBottom: '1rem' }}>This week's narrative</h2>
        <InsightCard insight={person.latest_insight} />
      </section>

      <section>
        <h2 style={{ marginBottom: '1rem' }}>Recent events</h2>
        <EventTimeline events={events} />
      </section>
    </div>
  );
}
