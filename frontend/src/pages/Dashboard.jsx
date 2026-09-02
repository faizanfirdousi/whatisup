import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { api } from '../api/client';
import { Loader } from '../components/Loader';
import { HeroBanner } from '../components/HeroBanner';
import { StoryCard } from '../components/StoryCard';
import { CloseCircleCard } from '../components/CloseCircleCard';
import { NetworkStorySection } from '../components/NetworkStorySection';
import { readStoredPeriod } from '../period';

export function Dashboard() {
  const [period, setPeriod] = useState(readStoredPeriod);
  const { data: digest, loading, error } = useApi(api.getDigestV2, [period]);
  const { data: highlights, refetch: refetchHighlights } = useApi(api.getHighlightsRefresh, [period]);

  useEffect(() => {
    let acked = false;
    const ack = () => {
      if (acked) return;
      acked = true;
      api.ackHighlights({ surface: 'dashboard' }).catch(() => {});
    };
    const dwell = setTimeout(ack, 8000);
    const onHide = () => {
      if (document.visibilityState === 'hidden') ack();
    };
    document.addEventListener('visibilitychange', onHide);
    return () => {
      clearTimeout(dwell);
      document.removeEventListener('visibilitychange', onHide);
    };
  }, []);

  useEffect(() => {
    if (highlights?.collecting) {
      const t = setTimeout(() => refetchHighlights(), 3000);
      return () => clearTimeout(t);
    }
  }, [highlights?.collecting, refetchHighlights]);

  const stories = useMemo(() => digest?.stories || [], [digest]);
  const closeCircle = digest?.close_circle || [];
  const intelligence = digest?.network_intelligence || {};
  const hasContent = stories.length > 0 || (intelligence?.story?.stories || []).length > 0;

  if (loading) return <Loader />;

  if (error) {
    return <div className="panel" style={{ padding: '2rem' }}>Could not load digest: {error}</div>;
  }

  return (
    <div className="dashboard-v2">
      <HeroBanner digest={digest} period={period} onPeriodChange={setPeriod} />

      {highlights?.collecting && !hasContent && (
        <div className="collecting-banner">Collecting your network. New activity will appear here shortly.</div>
      )}

      <NetworkStorySection intelligence={intelligence} />

      <section className="dashboard-section">
        <div className="section-heading">
          <h2>Worth your attention</h2>
          <Link to="/network">Explore full network</Link>
        </div>
        {stories.length === 0 ? (
          <div className="panel empty-panel">
            Nothing worth surfacing yet. We will highlight meaningful changes here as your network becomes active.
          </div>
        ) : (
          <div className="story-grid">
            {stories.map((story) => (
              <StoryCard key={story.id} story={story} />
            ))}
          </div>
        )}
      </section>

      {closeCircle.length > 0 && (
        <section className="dashboard-section">
          <div className="section-heading">
            <h2>Close circle</h2>
          </div>
          <div className="close-circle-grid">
            {closeCircle.map((item) => (
              <CloseCircleCard key={item.person.id} item={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
