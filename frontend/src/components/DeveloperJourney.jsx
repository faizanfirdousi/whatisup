import React from 'react';

export function DeveloperJourney({ phases, milestones }) {
  const months = phases || [];
  const marks = milestones || [];

  if (!months.length && !marks.length) {
    return (
      <div className="glass-panel empty-panel">
        Not enough history yet to reconstruct a trajectory.
      </div>
    );
  }

  return (
    <div className="developer-journey">
      {months.length > 0 && (
        <div className="journey-phases">
          {months.map((phase) => (
            <article key={phase.month_key || phase.month} className="journey-phase">
              <h4>{phase.month}</h4>
              <p>{phase.summary}</p>
              {(phase.technologies || []).length > 0 && (
                <p className="journey-techs">{phase.technologies.join(' · ')}</p>
              )}
            </article>
          ))}
        </div>
      )}
      {marks.length > 0 && (
        <div className="journey-milestones">
          <h4>Milestones</h4>
          <ul>
            {marks.map((mark) => (
              <li key={`${mark.kind}:${mark.label}`}>
                <strong>{mark.label}</strong>
                <span>{mark.detail}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
