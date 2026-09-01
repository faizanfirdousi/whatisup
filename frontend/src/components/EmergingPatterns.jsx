import React from 'react';
import { GitFork, Layers } from 'lucide-react';

export function EmergingPatterns({ patterns }) {
  const items = patterns || [];

  return (
    <section className="emerging-patterns">
      <div className="section-heading">
        <h2>Emerging patterns</h2>
      </div>
      {items.length === 0 ? (
        <div className="glass-panel empty-panel">No broader network pattern is visible yet.</div>
      ) : (
        <div className="emerging-grid">
          {items.map((item, index) => {
            const Icon = item.type === 'shared_repo' ? GitFork : Layers;
            return (
              <article key={`${item.type}:${item.repo || item.headline}:${index}`} className="emerging-card">
                <Icon size={18} />
                <h3>{item.headline}</h3>
                <p>
                  {item.people_count || 0} {(item.people_count || 0) === 1 ? 'person' : 'people'}
                  {item.repo ? ` in ${item.repo}` : ''}
                </p>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
