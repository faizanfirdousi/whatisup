import React from 'react';
import { Link } from 'react-router-dom';

export function NetworkStorySection({ intelligence }) {
  const stories = intelligence?.story?.stories || [];

  if (!stories.length) {
    return (
      <section className="network-story-section">
        <div className="section-heading">
          <h2>Active technologies across your network</h2>
        </div>
        <div className="panel empty-panel">
          Patterns will appear here as activity accumulates across your network.
        </div>
      </section>
    );
  }

  return (
    <section className="network-story-section">
      <div className="section-heading">
        <h2>Active technologies across your network</h2>
        <Link to="/network">Explore all technologies</Link>
      </div>
      <div className="network-stories-grid">
        {stories.map((item) => (
          <article key={item.id} className="network-story-card panel">
            <h3>{item.title}</h3>
            <p>{item.body}</p>
            {item.tech && (
              <Link to={`/network?tech=${encodeURIComponent(item.tech)}`} className="compact-link">
                Explore {item.tech}
              </Link>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
