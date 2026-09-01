import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { TechBadge } from './TechBadge';

export function CloseCircleCard({ item }) {
  const person = item.person || {};
  const repos = item.active_repos || [];
  const techs = item.technologies || [];

  return (
    <article className="close-circle-card">
      <div className="close-circle-head">
        <img
          src={person.avatar_url || `https://github.com/${person.github_username}.png`}
          alt={person.github_username}
        />
        <div>
          <h3>{person.display_name || person.github_username}</h3>
          <p>@{person.github_username}</p>
        </div>
      </div>
      {item.current_focus && (
        <p className="current-focus">
          Currently focused on: <span>{item.current_focus}</span>
        </p>
      )}
      {item.recent_change && (
        <p className="recent-change">{item.recent_change}</p>
      )}
      {(item.meaningful_changes || 0) > 0 && (
        <p className="meaningful-count">
          {item.meaningful_changes} meaningful{' '}
          {item.meaningful_changes === 1 ? 'change' : 'changes'}
        </p>
      )}
      {techs.length > 0 && (
        <div className="story-techs">
          {techs.map((tech) => (
            <TechBadge key={tech} name={tech} />
          ))}
        </div>
      )}
      {repos.length > 0 && <p className="repo-list">{repos.slice(0, 3).join(', ')}</p>}
      <Link to={`/person/${person.id}`} className="compact-link">
        Open profile <ArrowUpRight size={14} />
      </Link>
    </article>
  );
}
