import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { TechBadge } from './TechBadge';

export function YourRecentDirection({ direction }) {
  if (!direction) return null;

  const techs = direction.technologies || [];
  const repos = direction.recent_repos || [];

  return (
    <section className="dashboard-section your-direction-section">
      <div className="section-heading">
        <h2>Your recent direction</h2>
        {direction.person_id && (
          <Link to={`/person/${direction.person_id}`} className="compact-link">
            Your profile <ArrowUpRight size={14} />
          </Link>
        )}
      </div>
      <article className="your-direction-card glass-panel">
        {techs.length > 0 && (
          <div className="your-direction-block">
            <h3>Recently focused on</h3>
            <div className="story-techs">
              {techs.map((tech) => (
                <TechBadge key={tech} name={tech} />
              ))}
            </div>
          </div>
        )}
        {repos.length > 0 && (
          <div className="your-direction-block">
            <h3>Recent work</h3>
            <p className="repo-list">{repos.join('\n')}</p>
          </div>
        )}
        {direction.network_overlap && (
          <div className="your-direction-block">
            <h3>Network overlap</h3>
            <p>{direction.network_overlap}</p>
          </div>
        )}
        {!techs.length && !repos.length && !direction.network_overlap && direction.focus && (
          <p className="current-focus">
            Recently focused on: <span>{direction.focus}</span>
          </p>
        )}
      </article>
    </section>
  );
}
