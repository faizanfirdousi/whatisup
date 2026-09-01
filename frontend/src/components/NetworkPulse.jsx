import React from 'react';
import { ArrowDown, ArrowRight, ArrowUp } from 'lucide-react';

function directionIcon(direction) {
  if (direction === 'up') return <ArrowUp size={14} />;
  if (direction === 'down') return <ArrowDown size={14} />;
  return <ArrowRight size={14} />;
}

export function NetworkPulse({ pulse }) {
  if (!pulse) return null;
  const rows = [
    { key: 'more_active', label: 'More active', value: pulse.more_active || 0, icon: ArrowUp },
    { key: 'steady', label: 'Steady', value: pulse.steady || 0, icon: ArrowRight },
    { key: 'quiet', label: 'Quiet', value: pulse.quiet || 0, icon: ArrowDown },
  ];
  const total = rows.reduce((sum, row) => sum + row.value, 0) || 1;

  return (
    <section className="network-pulse">
      <div className="section-heading">
        <h2>Network pulse</h2>
      </div>
      <div className="pulse-grid">
        <div className="pulse-bars glass-panel">
          {rows.map((row) => {
            const Icon = row.icon;
            return (
              <div key={row.key} className="pulse-row">
                <div className="pulse-label"><Icon size={16} /> {row.label}</div>
                <div className="pulse-track">
                  <span style={{ width: `${Math.max(8, (row.value / total) * 100)}%` }} />
                </div>
                <strong>{row.value}</strong>
              </div>
            );
          })}
        </div>
        <div className="top-tech-panel glass-panel">
          <h3>Top technologies</h3>
          <div className="top-tech-list">
            {(pulse.top_technologies || []).length === 0 ? (
              <p>No technology pattern yet.</p>
            ) : (
              pulse.top_technologies.map((tech) => (
                <span key={`${tech.name}:${tech.direction}`} className={`tech-trend trend-${tech.direction || 'steady'}`}>
                  {tech.name} {directionIcon(tech.direction)}
                </span>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
