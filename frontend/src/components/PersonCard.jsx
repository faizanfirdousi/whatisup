import React from 'react';
import { Link } from 'react-router-dom';

export function PersonCard({ person }) {
  const score = person.latest_insight?.significance_total || 0;
  let scoreClass = 'badge-score';
  if (score >= 15) scoreClass += ' high';
  if (score >= 25) scoreClass += ' very-high';

  return (
    <Link to={`/person/${person.id}`} className="glass-card" style={{ display: 'block' }}>
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
        <img
          src={person.avatar_url || `https://github.com/${person.github_username}.png`}
          alt={person.github_username}
          style={{ width: '48px', height: '48px', borderRadius: '50%' }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {person.display_name || person.github_username}
            </h3>
            <span className={`badge ${scoreClass}`}>Score: {score}</span>
          </div>
          <p style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
            @{person.github_username}
            {person.is_close ? ' · close' : ''}
          </p>
          {person.latest_insight && (
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {person.latest_insight.narrative_text}
            </p>
          )}
          {(person.top_repos || []).length > 0 && (
            <p style={{ marginTop: '0.4rem', color: 'var(--text-tertiary)', fontSize: '0.75rem' }}>
              {person.event_count ? `${person.event_count} events · ` : ''}
              {person.top_repos.join(', ')}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}
