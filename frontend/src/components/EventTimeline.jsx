import React from 'react';

export function EventTimeline({ events }) {
  if (!events || events.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '1.25rem', color: 'var(--text-tertiary)' }}>
        No events collected yet.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {events.map((event) => (
        <div key={event.id} className="glass-card" style={{ padding: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
            <strong>{event.event_type.replaceAll('_', ' ')}</strong>
            <span className="badge badge-score">+{event.significance_score}</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            {event.repo_full_name || 'unknown repo'}
          </p>
          <p style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
            {event.occurred_at ? new Date(event.occurred_at).toLocaleString() : ''}
          </p>
        </div>
      ))}
    </div>
  );
}
