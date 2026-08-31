import React from 'react';
import { Users, Activity } from 'lucide-react';

export function StatsBar({ stats }) {
  if (!stats) return null;
  
  return (
    <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
      <div className="glass-panel" style={{ padding: '1.25rem', flex: 1, display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '0.75rem', borderRadius: 'var(--radius-full)', color: 'var(--accent-primary)' }}>
          <Users size={24} />
        </div>
        <div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Tracked Network</p>
          <p style={{ fontSize: '1.5rem', fontWeight: 600, fontFamily: 'Outfit' }}>{stats.total_people_tracked}</p>
        </div>
      </div>
      
      <div className="glass-panel" style={{ padding: '1.25rem', flex: 1, display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ background: 'rgba(139, 92, 246, 0.1)', padding: '0.75rem', borderRadius: 'var(--radius-full)', color: 'var(--accent-secondary)' }}>
          <Activity size={24} />
        </div>
        <div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Events Collected</p>
          <p style={{ fontSize: '1.5rem', fontWeight: 600, fontFamily: 'Outfit' }}>{stats.total_events_collected}</p>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '1.25rem', flex: 1, display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Weekly Insights</p>
          <p style={{ fontSize: '1.5rem', fontWeight: 600, fontFamily: 'Outfit' }}>{stats.total_insights ?? 0}</p>
        </div>
      </div>
    </div>
  );
}
