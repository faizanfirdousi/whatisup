import React from 'react';
import { ArrowDownRight, ArrowUpRight, GitBranch, Package, Rocket, Search, Wrench } from 'lucide-react';
import { Link } from 'react-router-dom';
import { TechBadge } from './TechBadge';

const ACTIVITY = {
  external_contribution: { label: 'External contribution', icon: GitBranch },
  release: { label: 'Release', icon: Rocket },
  new_project: { label: 'New project', icon: Package },
  deep_work: { label: 'Deep work', icon: Wrench },
  exploration: { label: 'Exploration', icon: Search },
  routine: { label: 'Active', icon: Wrench },
};

function TrendMark({ trend }) {
  if (!trend?.direction || trend.direction === 'steady') return null;
  const up = trend.direction === 'up';
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  const pct = Number.isFinite(trend.change_pct) ? Math.abs(trend.change_pct) : null;
  return (
    <span className={`trend-mark trend-${trend.direction}`}>
      <Icon size={14} />
      {pct != null ? `${pct}% vs prior` : up ? 'More active' : 'Quieter'}
    </span>
  );
}

export function StoryCard({ story }) {
  const person = story.person || {};
  const activity = ACTIVITY[story.activity_type] || ACTIVITY.routine;
  const Icon = activity.icon;

  return (
    <article className="story-card">
      <div className="story-card-top">
        <div className="story-card-meta">
          <span className={`badge activity-badge activity-${story.activity_type || 'routine'}`}>
            <Icon size={14} />
            {activity.label}
          </span>
          <TrendMark trend={story.trend} />
        </div>
        <img
          src={person.avatar_url || `https://github.com/${person.github_username}.png`}
          alt={person.github_username}
        />
      </div>
      <h3>{story.headline || `${person.display_name || person.github_username} was active`}</h3>
      <p className="story-summary">{story.summary}</p>
      {(story.technologies || []).length > 0 && (
        <div className="story-techs">
          {story.technologies.slice(0, 5).map((tech) => (
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
      <Link to={`/person/${person.id}`} className="story-link">
        View person <ArrowUpRight size={16} />
      </Link>
    </article>
  );
}
