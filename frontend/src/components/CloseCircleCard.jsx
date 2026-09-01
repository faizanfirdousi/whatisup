import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function CloseCircleCard({ item }) {
  const person = item.person || {};
  const repos = item.active_repos || [];

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
      <p className="current-focus">
        Currently focused on: <span>{item.current_focus || 'public GitHub activity'}</span>
      </p>
      <p className="meaningful-count">
        {item.meaningful_changes || 0} meaningful {(item.meaningful_changes || 0) === 1 ? 'change' : 'changes'}
      </p>
      {repos.length > 0 && <p className="repo-list">{repos.slice(0, 3).join(', ')}</p>}
      <Link to={`/person/${person.id}`} className="compact-link">
        Open profile <ArrowUpRight size={14} />
      </Link>
    </article>
  );
}
