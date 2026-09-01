import React from 'react';

export function InsightCard({ insight }) {
  if (!insight) {
    return (
      <div className="glass-panel" style={{ padding: '1.25rem', color: 'var(--text-tertiary)' }}>
        No weekly narrative yet. We'll write one once there is enough activity to summarize.
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <span className={`badge activity-badge activity-${insight.activity_type || 'routine'}`}>
          {(insight.activity_type || 'weekly narrative').replace(/_/g, ' ')}
        </span>
        <span style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
          {insight.week_start} → {insight.week_end}
        </span>
      </div>
      {insight.headline && (
        <h3 style={{ fontSize: '1.2rem', marginBottom: '0.75rem' }}>{insight.headline}</h3>
      )}
      <p style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>{insight.narrative_text}</p>
      {insight.why_it_matters && (
        <div className="why-it-matters" style={{ marginTop: '1rem' }}>
          <span>Why it matters</span>
          <p>{insight.why_it_matters}</p>
        </div>
      )}
    </div>
  );
}
