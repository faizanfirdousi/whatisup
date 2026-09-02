import React from 'react';

function Block({ width = '100%', height = '1rem', className = '' }) {
  return <div className={`skeleton-block ${className}`} style={{ width, height }} aria-hidden="true" />;
}

export function DashboardSkeleton() {
  return (
    <div className="dashboard-v2" aria-busy="true" aria-label="Loading digest">
      <div className="panel hero-banner skeleton-hero">
        <Block width="40%" height="0.85rem" />
        <Block width="min(100%, 520px)" height="2.4rem" className="skeleton-title" />
        <Block width="min(100%, 640px)" height="1rem" />
        <Block width="180px" height="1rem" />
      </div>
      <section className="dashboard-section">
        <Block width="280px" height="1.4rem" className="skeleton-title" />
        <div className="network-stories-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="panel network-story-card skeleton-card">
              <Block width="120px" height="1.1rem" />
              <Block width="100%" height="0.9rem" />
            </div>
          ))}
        </div>
      </section>
      <section className="dashboard-section">
        <Block width="220px" height="1.4rem" className="skeleton-title" />
        <div className="story-grid">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="story-card skeleton-card">
              <Block width="140px" height="0.75rem" />
              <Block width="80%" height="1.2rem" className="skeleton-title" />
              <Block width="100%" height="0.9rem" />
              <Block width="100%" height="0.9rem" />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function Loader() {
  return <DashboardSkeleton />;
}
