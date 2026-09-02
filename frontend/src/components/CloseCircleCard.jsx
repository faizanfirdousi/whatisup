import React from 'react';
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
      {item.direction_area && (
        <p className="current-focus">
          Recent direction: <span>{item.direction_area}</span>
        </p>
      )}
      {techs.length > 0 && (
        <div className="story-techs">
          {techs.map((tech) => (
            <TechBadge key={tech} name={tech} />
          ))}
        </div>
      )}
      {item.activity_summary && (
        <p className="meaningful-count">{item.activity_summary}</p>
      )}
      {repos.length > 0 && <p className="repo-list">{repos.slice(0, 3).join(', ')}</p>}
      <Link to={`/person/${person.id}`} className="compact-link">
        Open profile
      </Link>
    </article>
  );
}
