import React from 'react';

export function StatsBar({ stats }) {
  if (!stats) return null;

  return (
    <div className="stats-bar">
      <div className="panel stats-card">
        <p className="stats-label">Tracked network</p>
        <p className="stats-value">{stats.total_people_tracked}</p>
      </div>
      <div className="panel stats-card">
        <p className="stats-label">Events this week</p>
        <p className="stats-value">{stats.events_this_week ?? stats.total_events_collected}</p>
      </div>
      <div className="panel stats-card">
        <p className="stats-label">Weekly insights</p>
        <p className="stats-value">{stats.total_insights ?? 0}</p>
      </div>
    </div>
  );
}
