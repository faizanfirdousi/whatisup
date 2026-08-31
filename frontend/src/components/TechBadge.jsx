import React from 'react';

export function TechBadge({ name, confidence }) {
  return (
    <span className="badge" title={confidence != null ? `confidence ${confidence}` : undefined}>
      {name}
    </span>
  );
}
