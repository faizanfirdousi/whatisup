import React from 'react';
import { GitFork, Layers, TrendingUp } from 'lucide-react';

const ICONS = {
  growing_tech: TrendingUp,
  new_tech: Layers,
  shared_repo: GitFork,
  established_tech: Layers,
};

export function SharedActivity({ items }) {
  const rows = items || [];

  return (
    <section className="shared-activity">
      <div className="section-heading">
        <h2>Active across your network</h2>
      </div>
      {rows.length === 0 ? (
        <div className="glass-panel empty-panel">
          No broader network pattern is visible yet.
        </div>
      ) : (
        <div className="emerging-grid">
          {rows.map((item, index) => {
            const Icon = ICONS[item.type] || Layers;
            return (
              <article
                key={`${item.type}:${item.headline}:${index}`}
                className="emerging-card"
              >
                <Icon size={18} />
                <h3>{item.headline}</h3>
                <p>{item.detail}</p>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
