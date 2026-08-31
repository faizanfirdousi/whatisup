import React from 'react';

export function InsightCard({ insight }) {
  if (!insight) {
    return (
      <div className="glass-panel" style={{ padding: '1.25rem', color: 'var(--text-tertiary)' }}>
        No weekly narrative yet. Run the pipeline from Admin.
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <span className="badge badge-score">Score {insight.significance_total}</span>
        <span style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
          {insight.week_start} → {insight.week_end}
        </span>
      </div>
      <p style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>{insight.narrative_text}</p>
      <p style={{ marginTop: '0.75rem', color: 'var(--text-tertiary)', fontSize: '0.75rem' }}>
        {insight.model_used}
      </p>
    </div>
  );
}
