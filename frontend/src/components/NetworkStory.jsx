import React from 'react';
import { useNavigate } from 'react-router-dom';

export function NetworkStory({ story }) {
  const navigate = useNavigate();
  if (!story) return null;
  const bullets = story.bullets || [];
  const pulse = story.network_pulse || {};
  const sharedRepos = story.shared_repos || [];
  const topTechs = story.top_technologies || [];

  const openTech = (text) => {
    const match = text.match(/`([^`]+)`/) || text.match(/\b([a-z0-9.+#-]+)\b/i);
    const fromFacts = (story.cited_techs || [])[0];
    const tech = (story.cited_techs || []).find((t) => text.toLowerCase().includes(t.toLowerCase()));
    if (tech) navigate(`/network?tech=${encodeURIComponent(tech)}`);
    else if (match) navigate(`/network?tech=${encodeURIComponent(tech || fromFacts || match[1])}`);
  };

  return (
    <section style={{ marginBottom: '2.5rem' }}>
      <h2 style={{ marginBottom: '1rem' }}>Your network this week</h2>
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        {story.headline && (
          <p style={{ fontWeight: 600, marginBottom: '1rem' }}>{story.headline}</p>
        )}
        {bullets.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)' }}>No broader network pattern is visible yet.</p>
        ) : (
          <ul style={{ paddingLeft: '1.2rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {bullets.map((b) => (
              <li key={b}>
                <button
                  type="button"
                  onClick={() => openTech(b)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    font: 'inherit',
                    textAlign: 'left',
                    cursor: 'pointer',
                    padding: 0,
                  }}
                >
                  {b}
                </button>
              </li>
            ))}
          </ul>
        )}
        {(pulse.more_active || pulse.steady || pulse.quiet) && (
          <div className="network-story-pulse">
            <span>More active: {pulse.more_active || 0}</span>
            <span>Steady: {pulse.steady || 0}</span>
            <span>Quiet: {pulse.quiet || 0}</span>
          </div>
        )}
        {topTechs.length > 0 && (
          <div className="network-story-chips">
            {topTechs.map((tech) => (
              <button key={tech.name} type="button" onClick={() => navigate(`/network?tech=${encodeURIComponent(tech.name)}`)}>
                {tech.name} {tech.direction === 'up' ? 'up' : tech.direction === 'down' ? 'down' : 'steady'}
              </button>
            ))}
          </div>
        )}
        {sharedRepos.length > 0 && (
          <div className="network-story-shared">
            <p>Shared repositories</p>
            {sharedRepos.map((repo) => (
              <span key={repo.repo}>{repo.people_count} people in {repo.repo}</span>
            ))}
          </div>
        )}
        {story.interesting && (
          <div style={{ marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid var(--glass-border)' }}>
            <p style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-tertiary)', marginBottom: '0.5rem' }}>
              Something interesting is happening
            </p>
            <p style={{ color: 'var(--text-secondary)' }}>{story.interesting}</p>
          </div>
        )}
      </div>
    </section>
  );
}
