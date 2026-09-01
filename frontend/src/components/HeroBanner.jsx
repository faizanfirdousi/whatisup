import React from 'react';
import { Link } from 'react-router-dom';
import { PeriodSelector } from './PeriodSelector';

function timeGreeting(name) {
  const hour = new Date().getHours();
  const part = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  return name ? `${part}, ${name}` : part;
}

export function HeroBanner({ digest, period, onPeriodChange }) {
  const hero = digest?.network_intelligence?.hero || {};
  const signals = hero.signals || [];

  return (
    <section className="hero-banner">
      <div>
        <p className="eyebrow">{timeGreeting(digest?.owner_name)}</p>
        <h1>{hero.headline || "What's changing in your network"}</h1>
        <p className="hero-kicker">{hero.subhead}</p>
        {signals.length > 0 && (
          <div className="hero-signals" aria-label="Network signals">
            {signals.map((signal) => {
              const href = signal.direction === 'cluster' || signal.name === 'open-source'
                ? '/network'
                : `/network?tech=${encodeURIComponent(signal.name)}`;
              return (
                <Link
                  key={`${signal.name}:${signal.direction}`}
                  to={href}
                  className={`signal-chip signal-${signal.direction || 'steady'}`}
                  title={signal.description}
                >
                  {signal.label}
                </Link>
              );
            })}
          </div>
        )}
      </div>
      <PeriodSelector value={period} onChange={onPeriodChange} />
    </section>
  );
}
