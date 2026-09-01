import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { TechBadge } from './TechBadge';

export function ForYouSection({ intelligence }) {
  const forYou = intelligence?.for_you;
  if (!forYou) return null;

  const { direction, similar_people: similarPeople, relevant_cluster: cluster } = forYou;
  const hasContent = direction || (similarPeople || []).length || cluster;
  if (!hasContent) return null;

  return (
    <section className="for-you-section">
      <div className="section-heading">
        <h2>For you</h2>
      </div>
      <div className="for-you-stack">
        {direction && (
          <article className="for-you-block glass-panel">
            <h3>Your direction</h3>
            <p className="for-you-lead">{direction.headline}</p>
            <p>{direction.summary}</p>
          </article>
        )}

        {(similarPeople || []).length > 0 && (
          <article className="for-you-block glass-panel">
            <h3>People moving in a similar direction</h3>
            <ul className="similar-people-list">
              {similarPeople.map((person) => (
                <li key={person.person_id}>
                  <Link to={`/person/${person.person_id}`}>@{person.github_username}</Link>
                  <span>
                    {(person.technologies || []).join(' · ')}
                    {person.cluster ? ` · ${person.cluster}` : ''}
                  </span>
                </li>
              ))}
            </ul>
          </article>
        )}

        {cluster && (
          <article className="for-you-block glass-panel">
            <h3>A cluster relevant to you</h3>
            <p className="for-you-lead">{cluster.headline}</p>
            <p>{cluster.summary}</p>
            {(cluster.technologies || []).length > 0 && (
              <div className="story-techs">
                {cluster.technologies.map((tech) => (
                  <TechBadge key={tech} name={tech} />
                ))}
              </div>
            )}
            {cluster.explore_tech && (
              <Link
                to={`/network?tech=${encodeURIComponent(cluster.explore_tech)}`}
                className="compact-link"
              >
                Explore the cluster <ArrowUpRight size={14} />
              </Link>
            )}
          </article>
        )}
      </div>
    </section>
  );
}
