import React, { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { api } from '../api/client';
import { Loader } from '../components/Loader';
import { NetworkStory } from '../components/NetworkStory';
import { PeriodSelector } from '../components/PeriodSelector';
import { readStoredPeriod } from '../period';

const GROUPS = [
  { key: 'more_active', label: 'More active' },
  { key: 'steady', label: 'Steady' },
  { key: 'quiet', label: 'Quiet' },
];

export function Network() {
  const [searchParams] = useSearchParams();
  const tech = searchParams.get('tech') || '';
  const [period, setPeriod] = useState(readStoredPeriod);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const [syncing, setSyncing] = useState(false);
  const { data: digest, loading, error, refetch } = useApi(api.getDigestV2, [period]);
  const { data: story } = useApi(api.getNetworkStory, []);

  const people = useMemo(() => {
    const rows = digest?.people || [];
    const needle = query.trim().toLowerCase();
    return rows.filter((row) => {
      if (tech && !(row.technologies || []).some((name) => name.toLowerCase() === tech.toLowerCase())) {
        return false;
      }
      if (!needle) return true;
      const person = row.person || {};
      const hay = `${person.display_name || ''} ${person.github_username || ''} ${row.headline || ''} ${(row.technologies || []).join(' ')}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [digest, query, tech]);

  const grouped = useMemo(() => {
    const buckets = { more_active: [], steady: [], quiet: [] };
    people.forEach((row) => {
      const level = buckets[row.activity_level] ? row.activity_level : 'quiet';
      buckets[level].push(row);
    });
    return buckets;
  }, [people]);

  const toggle = async (row) => {
    try {
      await api.toggleCloseCircle(row.connection_id, !row.is_close);
      setStatus('');
      refetch();
    } catch (err) {
      setStatus(err.message);
    }
  };

  const syncFollowing = async () => {
    try {
      setSyncing(true);
      setStatus('Syncing your GitHub following list...');
      const result = await api.syncFollowing();
      if (result.added > 0) {
        setStatus(
          `Added ${result.added} new ${result.added === 1 ? 'person' : 'people'}. `
          + `${result.collecting ? 'Collecting their activity now.' : 'Collect will start shortly.'}`,
        );
      } else {
        setStatus(
          `Already up to date (${result.tracked_after} tracked).`
          + (result.collecting ? ' Refreshing activity.' : ''),
        );
      }
      refetch();
    } catch (err) {
      setStatus(err.message);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return <Loader />;
  if (error) {
    return <div className="glass-panel" style={{ padding: '2rem' }}>Could not load network: {error}</div>;
  }

  return (
    <div className="network-page">
      <header className="network-header">
        <div>
          <h1>Explore the network</h1>
          <p>
            {(digest?.people || []).length} people you are tracking
            {tech ? ` · filtered to ${tech}` : '. Home only shows the strongest stories.'}
          </p>
        </div>
        <div className="network-header-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={syncFollowing}
            disabled={syncing}
          >
            {syncing ? 'Syncing...' : 'Sync GitHub following'}
          </button>
          <PeriodSelector value={period} onChange={setPeriod} />
        </div>
      </header>

      <NetworkStory story={story} />

      <div className="network-toolbar">
        <input
          className="network-search"
          type="search"
          value={query}
          placeholder="Search by name, headline, or technology"
          onChange={(event) => setQuery(event.target.value)}
        />
        {tech && <Link to="/network">Clear tech filter</Link>}
      </div>

      {status && <p style={{ color: 'var(--warning)' }}>{status}</p>}

      {GROUPS.map((group) => {
        const rows = grouped[group.key] || [];
        if (!rows.length) return null;
        return (
          <section key={group.key} className="network-group">
            <div className="section-heading">
              <h2>{group.label}</h2>
              <span>{rows.length}</span>
            </div>
            <div className="network-grid">
              {rows.map((row) => {
                const person = row.person || {};
                return (
                  <article key={row.connection_id} className="glass-card network-person-card">
                    <div className="network-person-head">
                      <img
                        src={person.avatar_url || `https://github.com/${person.github_username}.png`}
                        alt={person.github_username}
                      />
                      <div>
                        <Link to={`/person/${person.id}`}>
                          {person.display_name || person.github_username}
                        </Link>
                        <p>@{person.github_username}</p>
                      </div>
                    </div>
                    {row.headline && <p className="network-headline">{row.headline}</p>}
                    {row.detail && <p className="network-focus">{row.detail}</p>}
                    <button
                      className={row.is_close ? 'btn btn-primary' : 'btn btn-secondary'}
                      onClick={() => toggle(row)}
                    >
                      {row.is_close ? 'Close circle' : 'Mark close'}
                    </button>
                  </article>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
