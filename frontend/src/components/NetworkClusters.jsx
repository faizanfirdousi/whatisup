import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { TechBadge } from './TechBadge';

export function NetworkClusters({ clusters }) {
  const items = clusters || [];
  if (!items.length) return null;

  return (
    <section className="network-clusters">
      <div className="section-heading">
        <h2>What your network is building</h2>
      </div>
      <div className="cluster-grid">
        {items.map((cluster) => (
          <article key={cluster.id} className="cluster-card glass-panel">
            <h3>{cluster.headline}</h3>
            <p>{cluster.summary}</p>
            {(cluster.technologies || []).length > 0 && (
              <div className="story-techs">
                {cluster.technologies.map((tech) => (
                  <TechBadge key={tech} name={tech} />
                ))}
              </div>
            )}
            {(cluster.repos || []).length > 0 && (
              <p className="cluster-repos">{cluster.repos.join(', ')}</p>
            )}
            {cluster.technologies?.[0] && (
              <Link
                to={`/network?tech=${encodeURIComponent(cluster.technologies[0])}`}
                className="compact-link"
              >
                Explore related people <ArrowUpRight size={14} />
              </Link>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
