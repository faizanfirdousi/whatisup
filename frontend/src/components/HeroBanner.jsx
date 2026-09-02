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
  const cta = hero.cta || { label: 'Explore network', href: '/network' };

  return (
    <section className="hero-banner panel">
      <div>
        <p className="eyebrow">{timeGreeting(digest?.owner_name)}</p>
        <h1>{hero.headline || "What's changing in your network"}</h1>
        <p className="hero-kicker">{hero.subhead}</p>
        <Link to={cta.href || '/network'} className="hero-cta">
          {cta.label}
        </Link>
      </div>
      <PeriodSelector value={period} onChange={onPeriodChange} />
    </section>
  );
}
