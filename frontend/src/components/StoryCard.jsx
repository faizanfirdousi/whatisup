import React from 'react';
import { Link } from 'react-router-dom';
import { TechBadge } from './TechBadge';

const ACTIVITY = {
  external_contribution: 'External contribution',
  release: 'Release',
  new_project: 'New project',
  deep_work: 'Deep work',
  exploration: 'Exploration',
  routine: 'Active',
};

export function StoryCard({ story }) {
  const person = story.person || {};
  const activity = ACTIVITY[story.activity_type] || ACTIVITY.routine;

  return (
    <article className="story-card">
      <div className="story-card-top">
        <span className={`badge activity-badge activity-${story.activity_type || 'routine'}`}>
          {activity}
        </span>
        <img
          src={person.avatar_url || `https://github.com/${person.github_username}.png`}
          alt={person.github_username}
        />
      </div>
      <h3>{story.headline || `${person.display_name || person.github_username} was active`}</h3>
      <p className="story-summary">{story.summary}</p>
      {(story.technologies || []).length > 0 && (
        <div className="story-techs">
          {story.technologies.map((tech) => (
            <TechBadge key={tech} name={tech} />
          ))}
        </div>
      )}
      {story.why_it_matters && (
        <div className="why-it-matters">
          <span>Why it matters</span>
          <p>{story.why_it_matters}</p>
        </div>
      )}
      {story.personal_note && (
        <p className="personal-note personal-note-strong">{story.personal_note}</p>
      )}
      <Link to={`/person/${person.id}`} className="story-link">
        View person
      </Link>
    </article>
  );
}
