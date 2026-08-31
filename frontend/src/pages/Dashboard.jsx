import React, { useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import { useSelectedOwner } from '../hooks/useSelectedOwner';
import { api } from '../api/client';
import { Loader } from '../components/Loader';
import { StatsBar } from '../components/StatsBar';
import { PersonCard } from '../components/PersonCard';
import { OwnerSelect } from '../components/OwnerSelect';

function PersonGrid({ people, empty }) {
  if (!people || people.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-tertiary)' }}>
        {empty}
      </div>
    );
  }
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
      {people.map((person) => (
        <PersonCard key={person.id} person={person} />
      ))}
    </div>
  );
}

export function Dashboard() {
  const { data: owners, loading: ownersLoading, error: ownersError } = useApi(api.getOwners, []);
  const { data: stats, loading: statsLoading } = useApi(api.getStats, []);
  const { ownerId, selectOwner } = useSelectedOwner(owners);

  const { data: digest, loading: digestLoading, error: digestError } = useApi(
    api.getDigest,
    [ownerId],
    { enabled: Boolean(ownerId) }
  );

  const loading = ownersLoading || statsLoading || (ownerId && digestLoading);
  const emptyReason = useMemo(() => {
    if (!owners || owners.length === 0) {
      return 'No owner yet. Open Admin, add a GitHub username, then run the pipeline.';
    }
    if (digest && digest.close_circle.length === 0 && digest.network_highlights.length === 0 && (digest.rest_of_network || []).length === 0) {
      return 'This owner has no connections. Add/reseed a GitHub user who actually follows people, then switch to that owner in the dropdown.';
    }
    return null;
  }, [owners, digest]);

  if (loading) return <Loader />;
  if (ownersError || digestError) {
    return <div className="glass-panel" style={{ padding: '2rem' }}>Could not load digest: {ownersError || digestError}</div>;
  }

  return (
    <div>
      <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', gap: '1.5rem', flexWrap: 'wrap' }}>
        <div>
          <h1 className="text-gradient" style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>This Week's Pulse</h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Public GitHub activity in the last {digest?.lookback_days ?? 30} days
            {digest?.owner?.github_username ? ` · seeded from @${digest.owner.github_username}` : ''}.
          </p>
        </div>
        <OwnerSelect owners={owners} ownerId={ownerId} onChange={selectOwner} />
      </header>

      <StatsBar stats={stats} />

      {emptyReason && (
        <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem', color: 'var(--text-secondary)' }}>
          {emptyReason}
        </div>
      )}

      {digest && (
        <>
          <section style={{ marginBottom: '3rem' }}>
            <h2 style={{ marginBottom: '1.5rem' }}>Close Circle</h2>
            <PersonGrid people={digest.close_circle} empty="Nobody marked close yet. Open Network and mark people." />
          </section>

          <section style={{ marginBottom: '3rem' }}>
            <h2 style={{ marginBottom: '1.5rem' }}>Network Highlights</h2>
            <PersonGrid people={digest.network_highlights} empty="Nobody reached significance 8+ in the last 30 days." />
          </section>

          <section>
            <h2 style={{ marginBottom: '1.5rem' }}>Rest of network</h2>
            <PersonGrid people={digest.rest_of_network || []} empty="No other connections for this owner." />
          </section>
        </>
      )}
    </div>
  );
}
