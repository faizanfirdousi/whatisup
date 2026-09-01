import React from 'react';
import { GitPullRequest, PackagePlus, Sparkles, Users } from 'lucide-react';
import { PeriodSelector } from './PeriodSelector';

function timeGreeting(name) {
  const hour = new Date().getHours();
  const part = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  return name ? `${part}, ${name}` : part;
}

function formatSummary(summary = {}) {
  const meaningful = summary.meaningful_changes || 0;
  const people = summary.people_count || 0;
  if (!meaningful) {
    return people ? `Your network of ${people} has been quiet` : 'Your developer network, summarized';
  }
  return `${meaningful} meaningful ${meaningful === 1 ? 'change' : 'changes'} across ${people} people`;
}

export function HeroBanner({ digest, period, onPeriodChange }) {
  const summary = digest?.summary || {};
  const peopleCount = summary.people_count
    || (digest?.network_pulse
      ? (digest.network_pulse.more_active || 0) + (digest.network_pulse.steady || 0) + (digest.network_pulse.quiet || 0)
      : 0);
  const displaySummary = { ...summary, people_count: peopleCount };

  return (
    <section className="hero-banner">
      <div>
        <p className="eyebrow">{timeGreeting(digest?.owner_name)}</p>
        <h1>{formatSummary(displaySummary)}</h1>
        <p className="hero-kicker">What changed in your developer network.</p>
        <div className="hero-stats" aria-label="Digest highlights">
          <span><GitPullRequest size={16} /> {summary.people_shipped || 0} shipped something</span>
          <span><PackagePlus size={16} /> {summary.new_projects || 0} new projects</span>
          <span><Sparkles size={16} /> {summary.interesting_repos || 0} high-signal repos</span>
          <span><Users size={16} /> {peopleCount} tracked</span>
        </div>
      </div>
      <PeriodSelector value={period} onChange={onPeriodChange} />
    </section>
  );
}
